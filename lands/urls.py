from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('map/', views.map_dashboard, name='map_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    path('parcels/', views.parcel_list, name='parcel_list'),
    path('parcels/add/', views.parcel_create, name='parcel_create'),
    path('parcels/<int:id>/', views.parcel_detail, name='parcel_detail'),
    path('parcels/<int:id>/edit/', views.parcel_edit, name='parcel_edit'),
    
    path('alerts/', views.alert_dashboard, name='alert_dashboard'),
    path('alerts/add/', views.alert_create, name='alert_create'),
    path('alerts/<int:id>/', views.alert_detail, name='alert_detail'),
    
    path('officers/', views.officer_management, name='officer_management'),
    
    # API endpoints for frontend interaction via HTMX / Leaflet JS
    path('api/parcels/', views.parcels_json_api, name='parcels_json'),
    path('run-scan/', views.run_scan_api, name='run_scan_api'),
    path('run-real-time-scan/', views.run_real_time_scan, name='run_real_time_scan'),
    path('api/load-dummy/', views.load_dummy_data, name='load_dummy_data'),
    path('api/export/parcels/', views.export_parcels_csv, name='export_parcels_csv'),
    path('api/latest-alerts/', views.latest_alerts_partial, name='latest_alerts_poll'),
]
