from django.contrib import admin
from .models import District, Officer, LandParcel, LandDocument, SatelliteImage, EncroachmentAlert, AuditLog

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'headquarters', 'collector_email', 'created_at')
    search_fields = ('name', 'headquarters')

@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'role', 'district', 'phone', 'is_active')
    list_filter = ('role', 'is_active', 'district')
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'user__last_name', 'phone')

@admin.register(LandParcel)
class LandParcelAdmin(admin.ModelAdmin):
    list_display = (
        'survey_number', 'district', 'classification', 
        'status', 'area_sqm', 'encroachment_risk_score', 
        'alert_count', 'last_satellite_scan'
    )
    list_filter = ('district', 'classification', 'status')
    search_fields = ('survey_number', 'taluk', 'village')

@admin.register(LandDocument)
class LandDocumentAdmin(admin.ModelAdmin):
    list_display = ('parcel', 'document_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('document_type',)
    search_fields = ('parcel__survey_number',)

@admin.register(SatelliteImage)
class SatelliteImageAdmin(admin.ModelAdmin):
    list_display = ('parcel', 'capture_date', 'image_type', 'source', 'cloud_coverage')
    list_filter = ('image_type', 'source')
    search_fields = ('parcel__survey_number',)

@admin.register(EncroachmentAlert)
class EncroachmentAlertAdmin(admin.ModelAdmin):
    list_display = (
        'parcel', 'alert_type', 'severity', 'status', 
        'detection_method', 'ml_confidence_score', 'created_at'
    )
    list_filter = ('status', 'severity', 'alert_type', 'detection_method')
    search_fields = ('parcel__survey_number',)
    readonly_fields = ('ml_confidence_score', 'change_percentage')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('officer', 'action', 'parcel', 'timestamp', 'ip_address')
    list_filter = ('action', 'officer')
    search_fields = ('officer__employee_id', 'parcel__survey_number', 'description')
    
    # Audit logs must never be editable or deletable
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
        
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
