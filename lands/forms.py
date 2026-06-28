from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import LandParcel, EncroachmentAlert

class LandParcelForm(forms.ModelForm):
    class Meta:
        model = LandParcel
        fields = [
            'survey_number', 'district', 'taluk', 'village', 
            'classification', 'area_sqm', 'status', 
            'latitude', 'longitude', 'gazette_reference', 'acquisition_date', 'description'
        ]
        widgets = {
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('survey_number', css_class='form-group col-md-4 mb-0'),
                Column('district', css_class='form-group col-md-4 mb-0'),
                Column('taluk', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('village', css_class='form-group col-md-4 mb-0'),
                Column('classification', css_class='form-group col-md-4 mb-0'),
                Column('area_sqm', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('status', css_class='form-group col-md-6 mb-0'),
                Column('acquisition_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('latitude', css_class='form-group col-md-6 mb-0'),
                Column('longitude', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'gazette_reference',
            'description',
            Submit('submit', 'Save Parcel')
        )

class EncroachmentAlertForm(forms.ModelForm):
    class Meta:
        model = EncroachmentAlert
        fields = ['parcel', 'alert_type', 'severity', 'description', 'evidence_photo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('parcel', css_class='form-group col-md-12 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('alert_type', css_class='form-group col-md-6 mb-0'),
                Column('severity', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            'evidence_photo',
            Submit('submit', 'Raise Alert', css_class='btn-danger')
        )
