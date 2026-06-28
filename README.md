# Government Land Records Management System (GLRMS)

A production-grade e-governance system combining GIS mapping, satellite imagery, and machine learning (ChangeFormer) to detect and manage land encroachments for Tamil Nadu, India.

## Tech Stack
- Backend: Python 3.11 + Django 4.2
- Database: PostgreSQL 15 + PostGIS
- GIS: Leaflet.js
- Frontend: HTML + HTMX + Bootstrap 5
- ML Detection: PyTorch + TorchGeo (pretrained ChangeFormer)
- Satellite Data: Sentinel Hub API

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database**
   ```bash
   createdb glrms_db
   psql -d glrms_db -c "CREATE EXTENSION postgis;"
   ```

3. **Environment Setup**
   Copy `.env.example` to `.env` and fill in your custom credentials.

4. **Initialize System**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py load_sample_data
   python manage.py runserver
   ```
