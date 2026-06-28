import django_filters
from django import forms
from .models import LandParcel, EncroachmentAlert

class LandParcelFilter(django_filters.FilterSet):
    survey_number = django_filters.CharFilter(lookup_expr='icontains', label='Search Survey No')
    
    class Meta:
        model = LandParcel
        fields = ['district', 'classification', 'status', 'survey_number']

class EncroachmentAlertFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name='created_at', lookup_expr='gte', 
        label='From Date', widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = django_filters.DateFilter(
        field_name='created_at', lookup_expr='lte', 
        label='To Date', widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = EncroachmentAlert
        fields = ['status', 'severity', 'alert_type', 'district']

    district = django_filters.ChoiceFilter(
        method='filter_by_district', 
        label='District'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import District
        
        # Populate dynamic district choices if the DB is ready
        try:
            districts = [(d.id, d.name) for d in District.objects.all()]
            self.filters['district'].extra['choices'] = districts
        except:
            pass

    def filter_by_district(self, queryset, name, value):
        if value:
            return queryset.filter(parcel__district_id=value)
        return queryset
