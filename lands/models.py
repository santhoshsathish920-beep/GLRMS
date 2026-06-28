from django.db import models
from django.contrib.auth.models import User

class District(models.Model):
    name = models.CharField(max_length=100, unique=True)
    headquarters = models.CharField(max_length=100)
    collector_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Officer(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'System Administrator'),
        ('DISTRICT_OFFICER', 'District Revenue Officer'),
        ('FIELD_OFFICER', 'Field Inspector'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=10)
    employee_id = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()} ({self.get_role_display()})"

class LandParcel(models.Model):
    CLASSIFICATION_CHOICES = [
        ('REVENUE', 'Revenue Land'),
        ('PORAMBOKE', 'Poramboke Land'),
        ('FOREST', 'Forest Land'),
        ('WATER', 'Water Body / Lake / River Buffer'),
        ('INSTITUTION', 'Public Institution Land'),
        ('ROAD', 'Road / Highway Reserve'),
    ]
    
    STATUS_CHOICES = [
        ('SAFE', 'Safe'),
        ('DISPUTED', 'Disputed'),
        ('ENCROACHED', 'Encroached'),
    ]

    survey_number = models.CharField(max_length=50, unique=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    taluk = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES)
    area_sqm = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SAFE')
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    last_checked = models.DateTimeField(null=True, blank=True)
    
    gazette_reference = models.CharField(max_length=255, blank=True, null=True)
    acquisition_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    
    last_satellite_scan = models.DateTimeField(null=True, blank=True)
    encroachment_risk_score = models.FloatField(default=0.0)
    
    created_by = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def alert_count(self):
        return self.alerts.exclude(status__in=['RESOLVED', 'CLOSED']).count()

    @property
    def is_high_risk(self):
        return self.encroachment_risk_score > 0.7

    def __str__(self):
        return f"{self.survey_number} - {self.district.name}"

class LandDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('PATTA', 'Patta'),
        ('CHITTA', 'Chitta'),
        ('FMB', 'FMB Sketch'),
        ('GAZETTE', 'Gazette Notification'),
        ('COURT', 'Court Order'),
        ('OTHER', 'Other Document'),
    ]
    
    parcel = models.ForeignKey(LandParcel, related_name='documents', on_delete=models.CASCADE)
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/parcels/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.parcel.survey_number}"

class SatelliteImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ('BEFORE', 'Before Image'),
        ('AFTER', 'After Image'),
        ('CURRENT', 'Current State'),
    ]

    parcel = models.ForeignKey(LandParcel, related_name='satellite_images', on_delete=models.CASCADE)
    image_file = models.ImageField(upload_to='satellite/parcels/')
    capture_date = models.DateField()
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES)
    source = models.CharField(max_length=100, default='Sentinel-2')
    cloud_coverage = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_image_type_display()} - {self.parcel.survey_number}"

class EncroachmentAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('CONSTRUCTION', 'Unauthorized Construction'),
        ('VEGETATION', 'Vegetation Clearing'),
        ('WATER', 'Water Body Encroachment'),
        ('BOUNDARY', 'Boundary Violation'),
        ('LAND_USE', 'Land Use Change'),
        ('OTHER', 'Other'),
    ]
    
    DETECTION_CHOICES = [
        ('ML_AUTO', 'ML Auto Detection'),
        ('SATELLITE', 'Satellite Manual Review'),
        ('FIELD', 'Field Officer Report'),
        ('PUBLIC', 'Public Complaint'),
    ]
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Under Investigation'),
        ('RESOLVED', 'Resolved'),
        ('ESCALATED', 'Escalated'),
        ('CLOSED', 'Closed'),
    ]

    parcel = models.ForeignKey(LandParcel, related_name='alerts', on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    detection_method = models.CharField(max_length=20, choices=DETECTION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    description = models.TextField()
    evidence_photo = models.ImageField(upload_to='evidence/', blank=True, null=True)
    
    before_image = models.ForeignKey(SatelliteImage, blank=True, null=True, related_name='alert_before', on_delete=models.SET_NULL)
    after_image = models.ForeignKey(SatelliteImage, blank=True, null=True, related_name='alert_after', on_delete=models.SET_NULL)
    
    ml_confidence_score = models.FloatField(blank=True, null=True)
    change_percentage = models.FloatField(blank=True, null=True)
    
    reported_by = models.ForeignKey(Officer, related_name='reported_alerts', on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(Officer, related_name='assigned_alerts', on_delete=models.SET_NULL, blank=True, null=True)
    resolved_by = models.ForeignKey(Officer, related_name='resolved_alerts', on_delete=models.SET_NULL, blank=True, null=True)
    resolved_date = models.DateField(blank=True, null=True)
    
    escalated_to_collector = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.parcel.survey_number}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('CREATE', 'Record Created'),
        ('UPDATE', 'Record Updated'),
        ('DELETE', 'Record Deleted'),
        ('SCAN', 'Satellite Scan Run'),
        ('ALERT', 'Alert Raised'),
        ('ESCALATE', 'Alert Escalated'),
        ('RESOLVE', 'Alert Resolved'),
        ('EXPORT', 'Data Exported'),
    ]

    officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    parcel = models.ForeignKey(LandParcel, on_delete=models.SET_NULL, null=True, blank=True)
    alert = models.ForeignKey(EncroachmentAlert, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_action_display()} at {self.timestamp}"
