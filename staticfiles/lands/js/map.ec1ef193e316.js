let map;
let markerLayer;

// Status colors
function getParcelColor(status) {
    if (status === 'SAFE') return '#2ecc71';      // green
    if (status === 'DISPUTED') return '#f39c12';     // orange
    if (status === 'ENCROACHED') return '#e74c3c';   // red
    if (status === 'RISK') return '#e74c3c';         // red for ML detected risk
    return '#3498db'; // default
}

function initMap() {
    const mapElement = document.getElementById('map');
    if (!mapElement) return;

    // Tamil Nadu Center fallback
    map = L.map('map').setView([11.1271, 78.6569], 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18, minZoom: 5, attribution: '© OpenStreetMap'
    }).addTo(map);

    markerLayer = L.layerGroup().addTo(map);

    // 1. ADD REAL-TIME GEE TILES (If available from scan)
    if (window.geeTileUrl) {
        console.log("Adding GEE Tile Layer:", window.geeTileUrl);
        L.tileLayer(window.geeTileUrl, {
            attribution: 'Map Data &copy; Google Earth Engine',
            opacity: 0.8
        }).addTo(map);

        if (window.geeBounds) {
            // geeBounds is usually [[lat, lon], [lat, lon]...]
            // GEE returns [ [lon, lat], ... ] often, so we might need to flip or use L.geoJSON
            map.fitBounds(L.latLngBounds(window.geeBounds.map(coord => [coord[1], coord[0]])));
        }
    } 
    // 2. FALLBACK TO IMAGE OVERLAY (If static result exists)
    else {
        const imageUrl = '/static/lands/risk_map.png?v=' + new Date().getTime();
        const imageBounds = window.scanBounds || [[11.12257, 78.65159], [11.13171, 78.66085]];
        
        const riskOverlay = L.imageOverlay(imageUrl, imageBounds, {
            opacity: 0.7,
            interactive: true,
            alt: 'Satellite Analysis Overlay'
        }).addTo(map);
        
        riskOverlay.bindPopup("<b>Satellite Analysis Overlay</b><br>Red areas indicate potential illegal occupation.");
    }

    loadParcels();
}

function loadParcels(filters = {}) {
    if (!map) return;
    let url = new URL('/api/parcels/', window.location.origin);
    Object.keys(filters).forEach(key => {
        if(filters[key]) url.searchParams.append(key, filters[key]);
    });

    fetch(url)
    .then(res => res.json())
    .then(data => {
        markerLayer.clearLayers();
        
        data.forEach(parcel => {
            if (parcel.latitude && parcel.longitude) {
                const marker = L.circleMarker([parcel.latitude, parcel.longitude], {
                    radius: 8,
                    fillColor: getParcelColor(parcel.status),
                    color: "#fff",
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                });

                let popupContent = `
                    <div class="p-2">
                        <h6 class="mb-1 text-primary">Survey No: ${parcel.survey_number}</h6>
                        <div class="small fw-bold text-muted mb-2">${parcel.district_name} | ${parcel.classification}</div>
                        <p class="mb-1 small"><strong>Area:</strong> ${parcel.area_sqm} sq.m</p>
                        <p class="mb-1 small"><strong>Status:</strong> ${parcel.status}</p>
                        <p class="mb-2 small"><strong>Risk Score:</strong> ${parcel.risk_score}</p>
                        <a href="/parcels/${parcel.id}/" class="btn btn-sm btn-outline-primary w-100">View Details</a>
                    </div>
                `;
                marker.bindPopup(popupContent);
                marker.addTo(markerLayer);
            }
        });

        if (data.length > 0) {
            const group = new L.featureGroup(markerLayer.getLayers());
            if (group.getLayers().length > 0) {
                map.fitBounds(group.getBounds(), {padding: [50,50]});
            }
        }
    })
    .catch(err => console.error("Error loading parcels", err));
}

function filterParcels() {
    let dist = document.getElementById('filter-district');
    let clas = document.getElementById('filter-class');
    let stat = document.getElementById('filter-status');
    
    let filters = {
        district: dist ? dist.value : '',
        classification: clas ? clas.value : '',
        status: stat ? stat.value : ''
    };
    loadParcels(filters);
}

document.addEventListener("DOMContentLoaded", function() {
    initMap();
    let filterBtn = document.getElementById('apply-filters-btn');
    if(filterBtn) { filterBtn.addEventListener('click', filterParcels); }
});
