import csv
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import models
from .models import District, Officer, LandParcel, LandDocument, SatelliteImage, EncroachmentAlert, AuditLog
from .forms import LandParcelForm, EncroachmentAlertForm
from .filters import LandParcelFilter, EncroachmentAlertFilter
from .serializers import LandParcelSerializer
from .utils import admin_required, district_officer_required, get_visible_parcels, get_visible_alerts, log_action
import random
import plotly.express as px
import plotly.offline as opy
import pandas as pd

def login_view(request):
    context = {}
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id', '').strip()
        password = request.POST.get('password', '')
        
        context['employee_id'] = employee_id

        if not employee_id or not password:
            context['error'] = "Please enter both Employee ID and password."
            return render(request, 'lands/login.html', context)

        try:
            # Query by the employee_id field on the Officer model
            officer = Officer.objects.get(employee_id=employee_id)
            
            # Authenticate using the linked user's username
            user = authenticate(request, username=officer.user.username, password=password)
            
            if user is not None:
                login(request, user)
                log_action(officer, 'LOGIN', request, details='User logged in successfully.')
                
                if officer.role == 'ADMIN':
                    return redirect('admin_dashboard')
                return redirect('map_dashboard')
            else:
                context['error'] = "Invalid password. Please try again."
        except Officer.DoesNotExist:
            context['error'] = "Invalid employee ID. No such officer exists."
            
    return render(request, 'lands/login.html', context)

@login_required
def logout_view(request):
    officer = getattr(request.user, 'officer', None)
    if officer:
        log_action(officer, 'LOGOUT', request, details='User logged out.')
    logout(request)
    return redirect('login')

@login_required
def map_dashboard(request):
    officer = getattr(request.user, 'officer', None)
    if not officer:
        return redirect('login')
        
    parcels = get_visible_parcels(officer)
    alerts = get_visible_alerts(officer)
    
    context = {
        'officer': officer,
        'districts': District.objects.all(),
        'total_parcels': parcels.count(),
        'active_alerts': alerts.filter(status__in=['OPEN', 'INVESTIGATING', 'ESCALATED']).count(),
        'resolved_alerts': alerts.filter(status='RESOLVED').count(),
        'high_risk_parcels': parcels.filter(encroachment_risk_score__gt=0.7).count()
    }
    
    # Check if a live GEE tile layer exists in the session
    context['gee_tile_url'] = request.session.get('gee_tile_url')
    context['gee_bounds'] = request.session.get('gee_bounds')
    output_path = os.path.join(settings.BASE_DIR, 'lands', 'static', 'lands', 'risk_map.png')
    context['scan_results_exist'] = os.path.exists(output_path)
    
    return render(request, 'lands/map_dashboard.html', context)

@login_required
@login_required
def parcels_json_api(request):
    officer = getattr(request.user, 'officer', None)
    parcels = get_visible_parcels(officer)
    
    district_id = request.GET.get('district')
    classification = request.GET.get('classification')
    status = request.GET.get('status')
    
    if district_id:
        parcels = parcels.filter(district_id=district_id)
    if classification:
        parcels = parcels.filter(classification=classification)
    if status:
        parcels = parcels.filter(status=status)
        
    serializer = LandParcelSerializer(parcels, many=True)
    return JsonResponse(serializer.data, safe=False)

@login_required
def parcel_list(request):
    officer = getattr(request.user, 'officer', None)
    queryset = get_visible_parcels(officer)
    
    parcel_filter = LandParcelFilter(request.GET, queryset=queryset)
    paginator = Paginator(parcel_filter.qs.order_by('-updated_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'filter': parcel_filter,
        'page_obj': page_obj
    }
    
    if hasattr(request, 'htmx') and request.htmx:
        return render(request, 'lands/partials/parcel_table.html', context)
    return render(request, 'lands/parcel_list.html', context)

@login_required
def parcel_detail(request, id):
    officer = getattr(request.user, 'officer', None)
    parcel = get_object_or_404(get_visible_parcels(officer), id=id)
    
    if request.method == 'POST' and hasattr(request, 'htmx') and request.htmx:
        doc_type = request.POST.get('document_type')
        doc_file = request.FILES.get('file')
        desc = request.POST.get('description', '')
        
        if doc_file and doc_type:
            LandDocument.objects.create(
                parcel=parcel,
                document_type=doc_type,
                file=doc_file,
                description=desc,
                uploaded_by=officer
            )
            log_action(officer, 'UPDATE', request, parcel=parcel, details=f'Uploaded document: {doc_type}')
            messages.success(request, 'Document uploaded successfully')
            
        return render(request, 'lands/partials/document_list.html', {'parcel': parcel})
        
    context = {
        'parcel': parcel,
        'alerts': parcel.alerts.all().order_by('-created_at'),
        'audit_logs': AuditLog.objects.filter(parcel=parcel).order_by('-timestamp')[:20],
        'doc_types': LandDocument.DOC_TYPE_CHOICES,
    }
    return render(request, 'lands/parcel_detail.html', context)

@login_required
@district_officer_required
def parcel_create(request):
    officer = getattr(request.user, 'officer', None)
    
    if request.method == 'POST':
        form = LandParcelForm(request.POST)
        if form.is_valid():
            parcel = form.save(commit=False)
            parcel.created_by = officer
            parcel.save()
            log_action(officer, 'CREATE', request, parcel=parcel, details='Created new land parcel manually.')
            messages.success(request, 'Land parcel created successfully.')
            return redirect('parcel_detail', id=parcel.id)
    else:
        form = LandParcelForm()
        
    return render(request, 'lands/parcel_form.html', {'form': form, 'title': 'Add New Parcel'})

@login_required
@district_officer_required
def parcel_edit(request, id):
    officer = getattr(request.user, 'officer', None)
    parcel = get_object_or_404(get_visible_parcels(officer), id=id)
    
    if request.method == 'POST':
        form = LandParcelForm(request.POST, instance=parcel)
        if form.is_valid():
            form.save()
            log_action(officer, 'UPDATE', request, parcel=parcel, details='Updated parcel details.')
            messages.success(request, 'Land parcel updated successfully.')
            return redirect('parcel_detail', id=parcel.id)
    else:
        form = LandParcelForm(instance=parcel)
        
    return render(request, 'lands/parcel_form.html', {'form': form, 'title': f'Edit Parcel {parcel.survey_number}'})

@login_required
def alert_dashboard(request):
    officer = getattr(request.user, 'officer', None)
    queryset = get_visible_alerts(officer)
    
    alert_filter = EncroachmentAlertFilter(request.GET, queryset=queryset)
    paginator = Paginator(alert_filter.qs.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'filter': alert_filter,
        'page_obj': page_obj,
        'open_count': queryset.filter(status='OPEN').count(),
        'investigating_count': queryset.filter(status='INVESTIGATING').count(),
        'resolved_count': queryset.filter(status='RESOLVED').count(),
        'escalated_count': queryset.filter(status='ESCALATED').count(),
        'critical_count': queryset.filter(severity='CRITICAL', status__in=['OPEN', 'INVESTIGATING']).count()
    }
    
    if hasattr(request, 'htmx') and request.htmx:
        return render(request, 'lands/partials/alert_table.html', context)
    return render(request, 'lands/alert_dashboard.html', context)

@login_required
def alert_detail(request, id):
    officer = getattr(request.user, 'officer', None)
    alert = get_object_or_404(get_visible_alerts(officer), id=id)
    
    if request.method == 'POST' and hasattr(request, 'htmx') and request.htmx:
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'resolve':
            alert.status = 'RESOLVED'
            alert.resolved_by = officer
            alert.resolved_date = timezone.now().date()
            alert.description += f"\n\n[Resolved by {officer.user.get_full_name()}]: {notes}"
            alert.save()
            log_action(officer, 'RESOLVE', request, parcel=alert.parcel, alert=alert, details='Alert resolved.')
            messages.success(request, 'Alert has been resolved.')
            
        elif action == 'escalate':
            if officer.role in ['ADMIN', 'DISTRICT_OFFICER']:
                alert.status = 'ESCALATED'
                alert.escalated_to_collector = True
                alert.description += f"\n\n[Escalated by {officer.user.get_full_name()}]: {notes}"
                alert.save()
                log_action(officer, 'ESCALATE', request, parcel=alert.parcel, alert=alert, details='Alert escalated to Collector.')
                messages.warning(request, 'Alert escalated successfully.')
                
        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(EncroachmentAlert.STATUS_CHOICES):
                alert.status = new_status
                alert.description += f"\n\n[Status updated to {new_status}]: {notes}"
                alert.save()
                log_action(officer, 'UPDATE', request, parcel=alert.parcel, alert=alert, details=f'Alert status changed to {new_status}')
                messages.success(request, 'Status updated.')
                
        return render(request, 'lands/partials/alert_status.html', {'alert': alert})
        
    return render(request, 'lands/alert_detail.html', {'alert': alert})

@login_required
def alert_create(request):
    officer = getattr(request.user, 'officer', None)
    
    if request.method == 'POST':
        form = EncroachmentAlertForm(request.POST, request.FILES)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.detection_method = 'FIELD'
            alert.reported_by = officer
            alert.save()
            log_action(officer, 'ALERT', request, parcel=alert.parcel, alert=alert, details='Manual alert raised.')
            messages.success(request, 'Encroachment alert raised successfully.')
            return redirect('alert_detail', id=alert.id)
    else:
        form = EncroachmentAlertForm()
        
    return render(request, 'lands/alert_form.html', {'form': form})

@login_required
@admin_required
def admin_dashboard(request):
    officer = getattr(request.user, 'officer', None)
    
    parcels = LandParcel.objects.all()
    alerts = EncroachmentAlert.objects.all()
    
    district_counts = parcels.values('district__name').annotate(count=models.Count('id'))
    status_counts = alerts.values('status').annotate(count=models.Count('id'))
    
    district_df = pd.DataFrame(list(district_counts))
    if not district_df.empty:
        fig_dist = px.bar(district_df, x='district__name', y='count', title='Parcels by District')
        plot_dist = opy.plot(fig_dist, auto_open=False, output_type='div')
    else:
        plot_dist = "<div>No data available</div>"
        
    status_df = pd.DataFrame(list(status_counts))
    if not status_df.empty:
        fig_status = px.pie(status_df, names='status', values='count', title='Alert Status Breakdown')
        plot_status = opy.plot(fig_status, auto_open=False, output_type='div')
    else:
        plot_status = "<div>No data available</div>"
    
    context = {
        'total_parcels': parcels.count(),
        'total_alerts': alerts.count(),
        'active_alerts_count': alerts.filter(status__in=['OPEN', 'INVESTIGATING', 'ESCALATED']).count(),
        'total_officers': Officer.objects.count(),
        'districts_count': District.objects.count(),
        'plot_dist': plot_dist,
        'plot_status': plot_status,
        'recent_logs': AuditLog.objects.order_by('-timestamp')[:20],
        'latest_scan': parcels.order_by('-last_satellite_scan').first().last_satellite_scan if parcels.exists() else None
    }
    return render(request, 'lands/admin_dashboard.html', context)

@login_required
@admin_required
def run_scan_api(request):
    if request.method == 'POST':
        from .services import run_automated_monitoring
        from django.utils import timezone as tz

        officer = getattr(request.user, 'officer', None)
        start_time = tz.now()

        try:
            success = run_automated_monitoring()
        except Exception as exc:
            return HttpResponse(
                f'<div class="alert alert-danger border-0 tn-shadow">'
                f'<strong><i class="fas fa-times-circle me-2"></i>Scan Error</strong><br>'
                f'{exc}</div>',
                status=500
            )

        elapsed = (tz.now() - start_time).seconds

        if success:
            # Compute fresh counts for the response
            new_alerts = EncroachmentAlert.objects.filter(
                detection_method='ML_AUTO',
                status='OPEN',
                created_at__gte=start_time
            ).count()
            encroached = LandParcel.objects.filter(status='ENCROACHED').count()

            log_action(
                officer, 'SCAN', request,
                details=f'Automated scan complete. {new_alerts} new alert(s) raised.'
            )
            return HttpResponse(f"""
            <div class="alert alert-danger tn-shadow border-0 animate__animated animate__fadeIn">
                <strong><i class="fas fa-satellite me-2"></i>Scan Complete — Risk Detected!</strong>
                <hr class="my-2">
                <div class="row text-center">
                    <div class="col-4">
                        <div class="fw-bold fs-5 text-danger">{encroached}</div>
                        <div class="small text-muted">Encroached Parcels</div>
                    </div>
                    <div class="col-4">
                        <div class="fw-bold fs-5 text-warning">{new_alerts}</div>
                        <div class="small text-muted">New Alerts Raised</div>
                    </div>
                    <div class="col-4">
                        <div class="fw-bold fs-5 text-info">{elapsed}s</div>
                        <div class="small text-muted">Scan Duration</div>
                    </div>
                </div>
                <div class="mt-2 small text-muted">
                    <i class="fas fa-clock me-1"></i>Completed at {tz.localtime(tz.now()).strftime('%H:%M:%S IST')}
                </div>
            </div>
            """)
        else:
            return HttpResponse("""
            <div class="alert alert-warning border-0 tn-shadow">
                <strong><i class="fas fa-exclamation-triangle me-2"></i>Scan Incomplete</strong><br>
                <span class="small">GEE is unavailable — analysis ran on fallback mock data, or
                no parcels with GPS coordinates exist. Check <code>logs/monitoring.log</code>
                for details.</span>
            </div>
            """)

    return HttpResponse("Invalid request", status=400)


@login_required
@admin_required
def load_dummy_data(request):
    # Create Districts
    districts_data = [
        {'name': 'Chennai', 'hq': 'Chennai'},
        {'name': 'Madurai', 'hq': 'Madurai'},
        {'name': 'Coimbatore', 'hq': 'Coimbatore'},
        {'name': 'Vellore', 'hq': 'Vellore'},
    ]
    
    created_districts = []
    for d in districts_data:
        obj, created = District.objects.get_or_create(name=d['name'], defaults={'headquarters': d['hq'], 'collector_email': f'collector.{d["name"].lower()}@tn.gov.in'})
        created_districts.append(obj)
    
    # Create Parcells in TN
    # Coordinates for TN roughly 8 to 13 N, 76 to 80 E
    base_lat = 11.1271
    base_lon = 78.6569
    
    parcels_count = 15
    officer = getattr(request.user, 'officer', None)
    
    for i in range(parcels_count):
        lat = base_lat + (random.random() - 0.5) * 2
        lon = base_lon + (random.random() - 0.5) * 2
        
        survey = f"TN/{random.randint(100,999)}/{random.randint(1,50)}"
        status = random.choice(['SAFE', 'SAFE', 'SAFE', 'DISPUTED'])
        
        LandParcel.objects.get_or_create(
            survey_number=survey,
            defaults={
                'district': random.choice(created_districts),
                'taluk': 'Sample Taluk',
                'village': 'Sample Village',
                'classification': random.choice(['REVENUE', 'PORAMBOKE', 'WATER']),
                'area_sqm': random.uniform(500, 5000),
                'status': status,
                'latitude': lat,
                'longitude': lon,
                'created_by': officer
            }
        )
    
    messages.success(request, f"Loaded dummy land data for demonstration.")
    return redirect('admin_dashboard')

@login_required
@admin_required
def officer_management(request):
    officers = Officer.objects.all()
    return render(request, 'lands/officer_management.html', {'officers': officers})

@login_required
@admin_required
def export_parcels_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="land_parcels.csv"'

    writer = csv.writer(response)
    writer.writerow(['Survey Number', 'District', 'Taluk', 'Village', 'Classification', 'Area Sqm', 'Status', 'Risk Score'])

    parcels = LandParcel.objects.all()
    for p in parcels:
        writer.writerow([
            p.survey_number, p.district.name, p.taluk, p.village, 
            p.get_classification_display(), p.area_sqm, 
            p.get_status_display(), p.encroachment_risk_score
        ])
        
    officer = getattr(request.user, 'officer', None)
    log_action(officer, 'EXPORT', request, details='Exported full parcel dataset to CSV.')
    return response

@login_required
def latest_alerts_partial(request):
    """
    Returns the latest 5 alerts for HTMX polling.
    """
    officer = getattr(request.user, 'officer', None)
    alerts = get_visible_alerts(officer).filter(status='OPEN').order_by('-created_at')[:5]
    return render(request, 'lands/partials/latest_alerts_poll.html', {'recent_alerts': alerts})

@login_required
@admin_required
def run_real_time_scan(request):
    """
    Triggers the upgraded GEE-based real-time sentinel-2 scan.
    Returns JSON with the GEE MapId tiles for live Leaflet visualization.
    """
    if request.method == 'POST':
        from detection.gee_utils import run_analysis
        from django.utils import timezone as tz
        
        start_time = tz.now()
        results = run_analysis()
        elapsed = (tz.now() - start_time).seconds
        
        if results.get('status') == 'success':
            messages.success(request, f"Satellite Scan Complete. Found {results['encroached_count']} encroachments.")
            
            # Store tile information in session for the map dashboard to pick up
            request.session['gee_tile_url'] = results.get('tile_url')
            request.session['gee_bounds'] = results.get('bounds')
            
            # Map result fields for the frontend
            results['elapsed'] = elapsed
            results['new_alerts'] = results.get('alerts_created', 0)
            results['encroached'] = results.get('encroached_count', 0)
            
            # If HTMX request, render the results partial (which can trigger JS for the map)
            if request.headers.get('HX-Request'):
                # We also want to pass tile info to the partial so it can trigger map updates
                return render(request, 'lands/partials/scan_results.html', {'results': results})
            return JsonResponse(results)
            
        else:
            messages.warning(request, f"GEE Scan Issue: {results.get('message', 'Unknown failure')}")
            if request.headers.get('HX-Request'):
                 return render(request, 'lands/partials/scan_results.html', {'results': results})
            return JsonResponse(results, status=400)
            
    return HttpResponse("Method not allowed", status=405)
