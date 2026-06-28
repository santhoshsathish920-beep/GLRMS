"""
Google Earth Engine (GEE) Service
==================================
Authenticates with GEE using a service account key and fetches
Sentinel-2 NDVI imagery for a specified Region of Interest (ROI).

Setup:
  1. Create a GEE project at https://earthengine.google.com/
  2. Create a Service Account and download the JSON key.
  3. Save it as 'gee_key.json' in the project root.
  4. Grant the service account 'Earth Engine' role.
"""

import os
import logging

logger = logging.getLogger('glrms.monitoring')

_GEE_INITIALIZED = False


def initialize_ee():
    """
    Initialize Earth Engine. Uses service account if gee_key.json exists,
    otherwise falls back to user auth (requires `earthengine authenticate`).
    Returns True on success, False on failure.
    """
    global _GEE_INITIALIZED

    if _GEE_INITIALIZED:
        return True

    try:
        import ee
        from django.conf import settings

        key_path = getattr(settings, 'GEE_KEY_PATH', 'gee_key.json')

        if os.path.exists(key_path):
            import json
            with open(key_path, 'r') as f:
                key_data = json.load(f)
            credentials = ee.ServiceAccountCredentials(
                key_data['client_email'], key_path
            )
            ee.Initialize(credentials)
            logger.info(f'GEE initialized with Service Account: {key_data["client_email"]}')
        else:
            # Attempt user-based auth (dev environment)
            ee.Initialize()
            logger.info('GEE initialized with user credentials.')

        _GEE_INITIALIZED = True
        return True

    except ImportError:
        logger.error('earthengine-api not installed. Run: pip install earthengine-api')
        return False
    except Exception as e:
        logger.error(f'GEE initialization failed: {e}')
        return False


def fetch_sentinel_ndvi(roi_coords, output_path):
    """
    Fetch the latest Sentinel-2 L2A NDVI image for an ROI and save as GeoTIFF.

    Args:
        roi_coords: List of [lon, lat] pairs defining a closed polygon.
        output_path: Full filesystem path to save the downloaded GeoTIFF.

    Returns:
        output_path on success, None on failure.
    """
    if not initialize_ee():
        return None

    try:
        import ee
        import requests
        from datetime import datetime, timedelta

        roi = ee.Geometry.Polygon(roi_coords)

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=45)  # 45-day window

        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(roi)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 15))
            .sort('system:time_start', False)  # Most recent first
        )

        size = collection.size().getInfo()
        if size == 0:
            logger.warning(
                'No Sentinel-2 imagery found in the last 45 days with cloud cover < 15%.'
            )
            return None

        logger.info(f'Found {size} Sentinel-2 scenes. Using most recent...')

        # Compute NDVI: (B8 - B4) / (B8 + B4)
        image = collection.first()
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI').clip(roi)

        # Get download URL (for small areas / dev)
        url = ndvi.getDownloadURL({
            'scale': 10,          # 10m Sentinel-2 native resolution
            'crs': 'EPSG:4326',
            'format': 'GEO_TIFF',
            'region': roi
        })

        logger.info('Downloading GEE imagery...')
        response = requests.get(url, timeout=120)

        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            logger.info(f'NDVI GeoTIFF saved to: {output_path}')
            return output_path
        else:
            logger.error(f'GEE download failed (HTTP {response.status_code}).')
            return None

    except Exception as e:
        logger.error(f'Error fetching GEE data: {e}', exc_info=True)
        return None
