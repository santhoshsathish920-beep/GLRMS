import os
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import LandParcel, EncroachmentAlert
from detection.processor import analyze_encroachment

logger = logging.getLogger('glrms.monitoring')


def run_automated_monitoring():
    """
    Full automated monitoring pipeline:
      1. Fetch all active parcels from the DB.
      2. Build Region of Interest and fetch GEE NDVI imagery.
      3. Run NDVI-based encroachment analysis using ML.
      4. Update parcel status and risk scores.
      5. Create alerts and send email notifications.
    """
    from .gee_service import fetch_sentinel_ndvi

    logger.info('Starting automated land monitoring pipeline...')

    parcels = LandParcel.objects.all()
    if not parcels.exists():
        logger.warning('No land parcels found in database. Aborting scan.')
        return False

    # Build parcel list (including geometries for masking)
    from shapely.geometry import shape

    parcels_data, lats, lons = [], [], []
    for p in parcels:
        if p.latitude and p.longitude:
            parcel_entry = {
                'id': p.id, 
                'lat': p.latitude, 
                'lon': p.longitude,
                'geom': None
            }
            
            # Extract geometry if available for precision masking
            if p.boundary_geojson:
                try:
                    parcel_entry['geom'] = shape(p.boundary_geojson)
                except Exception as e:
                    logger.warning(f"Could not parse geometry for parcel {p.id}: {e}")
            
            parcels_data.append(parcel_entry)
            lats.append(p.latitude)
            lons.append(p.longitude)

    if not parcels_data:
        logger.warning('No parcels with GPS coordinates found. Aborting scan.')
        return False

    logger.info(f'Scanning {len(parcels_data)} parcels...')

    # Build bounding box (ROI) for GEE
    margin = 0.02
    min_lat, max_lat = min(lats) - margin, max(lats) + margin
    min_lon, max_lon = min(lons) - margin, max(lons) + margin
    roi_coords = [
        [min_lon, min_lat], [max_lon, min_lat],
        [max_lon, max_lat], [min_lon, max_lat],
        [min_lon, min_lat]
    ]

    # Target path for downloaded GEE image
    data_dir = os.path.join(settings.BASE_DIR, 'detection', 'data')
    os.makedirs(data_dir, exist_ok=True)
    tif_path = os.path.join(data_dir, 'latest_ndvi.tif')

    logger.info('Fetching Sentinel-2 NDVI from Google Earth Engine...')
    gee_result = fetch_sentinel_ndvi(roi_coords, tif_path)

    if not gee_result:
        # Graceful fallback: use bundled mock TIF for offline / dev usage
        fallback_tif = os.path.join(settings.BASE_DIR, 'detection', 'land_change_mock.tif')
        if os.path.exists(fallback_tif):
            logger.warning(
                'GEE fetch failed. Falling back to mock TIF. '
                'Place gee_key.json in project root for live Sentinel-2 data.'
            )
            tif_path = fallback_tif
        else:
            logger.error('GEE failed and no fallback TIF found. Aborting scan.')
            return False

    # Run encroachment analysis
    output_image = os.path.join(
        settings.BASE_DIR, 'lands', 'static', 'lands', 'output.png'
    )
    logger.info(f'Running ML analysis on: {os.path.basename(tif_path)}')
    results = analyze_encroachment(tif_path, parcels_data, output_path=output_image)

    if not results:
        logger.warning('ML analysis returned no results.')
        return False

    # Update DB records and raise alerts
    alerts_created = 0
    encroached_count = 0

    for res in results:
        try:
            parcel = LandParcel.objects.get(id=res['id'])
            old_status = parcel.status
            parcel.status = res['status']
            parcel.encroachment_risk_score = res['risk_score']
            parcel.last_satellite_scan = timezone.now()
            parcel.save(update_fields=['status', 'encroachment_risk_score', 'last_satellite_scan'])

            if res['status'] == 'ENCROACHED':
                encroached_count += 1
                # Only create a new alert if no active one exists
                already_open = EncroachmentAlert.objects.filter(
                    parcel=parcel,
                    status__in=['OPEN', 'INVESTIGATING', 'ESCALATED']
                ).exists()

                if not already_open:
                    severity = 'CRITICAL' if res['risk_score'] > 0.8 else 'HIGH'
                    alert = EncroachmentAlert.objects.create(
                        parcel=parcel,
                        alert_type='CONSTRUCTION',
                        detection_method='ML_AUTO',
                        severity=severity,
                        status='OPEN',
                        description=(
                            f'AUTOMATED SATELLITE DETECTION: Illegal encroachment detected '
                            f'inside government land boundary.\n'
                            f'Survey No   : {parcel.survey_number}\n'
                            f'District    : {parcel.district.name}\n'
                            f'Village     : {parcel.village}\n'
                            f'NDVI Change : {res["ndvi_change"]:.4f}\n'
                            f'Confidence  : {res["risk_score"]:.2%}'
                        ),
                        ml_confidence_score=round(res['risk_score'], 4),
                        change_percentage=round(abs(res['ndvi_change']) * 100, 2)
                    )
                    alerts_created += 1
                    logger.warning(
                        f'[{severity}] New alert → Parcel {parcel.survey_number} '
                        f'(risk={res["risk_score"]:.2%})'
                    )
                    _send_encroachment_email(alert)

        except LandParcel.DoesNotExist:
            logger.error(f'Parcel ID {res["id"]} not found in database.')
        except Exception as e:
            logger.error(f'Error processing parcel {res.get("id")}: {e}', exc_info=True)

    logger.info(
        f'Scan complete | Parcels: {len(results)} | '
        f'Encroached: {encroached_count} | New Alerts: {alerts_created}'
    )
    return True


def _send_encroachment_email(alert):
    """Send email notification to the district collector for a critical alert."""
    try:
        collector_email = alert.parcel.district.collector_email
        if not collector_email:
            return

        base_url = f'http://{settings.ALLOWED_HOSTS[0]}'
        subject = (
            f'\U0001F6A8 CRITICAL: Illegal Encroachment — '
            f'Survey {alert.parcel.survey_number} ({alert.parcel.district.name})'
        )
        body = (
            f'Dear Collector / Revenue Officer,\n\n'
            f'An automated Sentinel-2 satellite scan has detected POTENTIAL ILLEGAL '
            f'ENCROACHMENT within government land boundaries:\n\n'
            f'  District    : {alert.parcel.district.name}\n'
            f'  Survey No.  : {alert.parcel.survey_number}\n'
            f'  Village     : {alert.parcel.village}\n'
            f'  Land Class  : {alert.parcel.get_classification_display()}\n'
            f'  ML Confidence : {alert.ml_confidence_score:.0%}\n'
            f'  Severity    : {alert.get_severity_display()}\n\n'
            f'Please take immediate action.\n'
            f'Portal link: {base_url}/alerts/{alert.id}/\n\n'
            f'— Government Land Monitoring System (GLRMS)\n'
            f'  Tamil Nadu Revenue Department'
        )
        send_mail(
            subject, body, settings.DEFAULT_FROM_EMAIL,
            [collector_email], fail_silently=True,
        )
        logger.info(f'Email sent to collector: {collector_email}')
    except Exception as e:
        logger.error(f'Email notification failed: {e}')
