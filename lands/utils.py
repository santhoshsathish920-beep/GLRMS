from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import LandParcel, EncroachmentAlert, AuditLog

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        officer = getattr(request.user, 'officer', None)
        if not officer or officer.role != 'ADMIN':
            messages.error(request, 'Access denied. Administrator privileges required.')
            return redirect('map_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def district_officer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        officer = getattr(request.user, 'officer', None)
        if not officer or officer.role == 'FIELD_OFFICER':
            messages.error(request, 'Access denied. District Officer privileges required.')
            return redirect('map_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def get_visible_parcels(officer):
    if not officer:
        return LandParcel.objects.none()
    if officer.role == 'ADMIN':
        return LandParcel.objects.all()
    else:
        return LandParcel.objects.filter(district=officer.district)

def get_visible_alerts(officer):
    if not officer:
        return EncroachmentAlert.objects.none()
    if officer.role == 'ADMIN':
        return EncroachmentAlert.objects.all()
    else:
        return EncroachmentAlert.objects.filter(parcel__district=officer.district)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_action(officer, action, request, parcel=None, alert=None, details=""):
    AuditLog.objects.create(
        officer=officer,
        action=action,
        parcel=parcel,
        alert=alert,
        description=details,
        ip_address=get_client_ip(request)
    )
