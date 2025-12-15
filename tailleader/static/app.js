// Register service worker for PWA support
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(registration => {
        console.log('ServiceWorker registered:', registration.scope);
      })
      .catch(err => {
        console.log('ServiceWorker registration failed:', err);
      });
  });
}

let currentWindow = '24h';
let chart;
let map;
let aircraftMarkers = {};
let showLabels = false;

// Configuration constants
const TOUCH_TAP_TOLERANCE = 15;  // Tolerance in pixels for tap recognition on touch devices

// Mapping of 3-letter ICAO airline codes to 2-letter FR24 codes
const airlineMap = {
  'AAL': 'AA', 'ABE': 'AB', 'ABX': 'AB', 'ACE': 'AC', 'ACA': 'AC', 'AIC': 'AI', 'AZA': 'AZ',
  'BAW': 'BA', 'BBD': 'BD', 'BJS': 'BJ', 'BOX': 'BA', 'BUA': 'BA',
  'CAL': 'UA', 'CCA': 'CA', 'CES': 'CE', 'CXA': 'CA', 'CHH': 'CH', 'CPA': 'CI', 'CIT': 'CI', 'CSN': 'CS', 'CTN': 'CT', 'CVA': 'CV',
  'DAL': 'DL', 'DLH': 'LH', 'DNV': 'DN',
  'EIN': 'EI', 'ELY': 'LY', 'EVA': 'BR',
  'FDX': 'FX', 'FFT': 'F9', 'FLY': 'F3', 'FRU': 'FU',
  'GJS': 'G4', 'GLF': 'GF',
  'HAL': 'HA', 'HDA': 'HD',
  'IBE': 'IB', 'ICE': 'FI', 'ICN': 'CI', 'INV': 'IN', 'IRA': 'IR',
  'JAL': 'JL', 'JBU': 'B6', 'JIA': 'OH', 'JZA': 'ZE',
  'KLM': 'KL', 'KLR': 'KL',
  'LAI': 'LA', 'LAX': 'LA', 'LDM': 'LD', 'LNI': 'JT', 'LOT': 'LO', 'LUX': 'LX',
  'MAL': 'MH', 'MAS': 'MH', 'MDA': 'MD', 'MEA': 'ME', 'MES': 'MS', 'MGX': 'MG',
  'NAX': 'NA', 'NKS': 'NK', 'NAI': 'NA',
  'OAL': 'OS', 'OKA': 'OK', 'ORL': 'OL', 'OXY': 'OX',
  'PAL': 'PR', 'PEC': 'PE', 'PIA': 'PK',
  'QFA': 'QF',
  'RYR': 'FR', 'RZO': 'R2',
  'SAB': 'SA', 'SAL': 'SQ', 'SAW': 'S7', 'SBE': 'SB', 'SBH': 'SB', 'SFJ': 'SF', 'SKW': 'OO', 'SLI': 'LS', 'SLK': 'BT', 'SOU': 'SO', 'SWA': 'WN', 'SWG': 'SW', 'SWR': 'SR', 'SYX': 'SY',
  'TAI': 'CI', 'TAP': 'TP', 'TAR': 'TR', 'THA': 'TG', 'THL': 'TL', 'TVS': 'TV', 'TVF': 'TV', 'TWA': 'TW', 'TWE': 'TW',
  'UAL': 'UA', 'UCA': 'UC', 'UIA': 'PS',
  'VBY': 'VB', 'VLG': 'VL', 'VIR': 'VS',
  'WAE': 'WA', 'WAW': 'WW', 'WDH': 'W2',
  'XRJ': 'XR',
  'ZZZ': 'ZZ'
};

// Convert 3-letter ICAO code to 2-letter FR24 code, preserving the flight number
function convertToFR24Code(icaoCallsign) {
  if (!icaoCallsign || icaoCallsign.length < 3) return icaoCallsign;
  const code3 = icaoCallsign.substring(0, 3).toUpperCase();
  const flightNumber = icaoCallsign.substring(3); // Keep everything after the first 3 chars
  const fr24Code = airlineMap[code3] || code3.substring(0, 2);
  return fr24Code + flightNumber;
}

async function fetchTop(window='24h') {
  const res = await fetch(`/api/top?window=${window}&limit=20`);
  return res.json();
}

async function fetchRecent() {
  const res = await fetch(`/api/recent?limit=50`);
  return res.json();
}

async function fetchLive() {
  const res = await fetch(`/api/live`);
  return res.json();
}

async function fetchStats() {
  const res = await fetch(`/api/stats`);
  return res.json();
}

async function fetchLookupStats() {
  const res = await fetch(`/api/lookup_stats`);
  return res.json();
}

function updateStats(stats) {
  if (stats.temp_c !== null) {
    document.getElementById('tempStat').textContent = `${stats.temp_c}°C`;
  }
  document.getElementById('ramStat').textContent = `${stats.memory_percent}%`;
  document.getElementById('cpuStat').textContent = `${stats.cpu_percent}%`;
}

async function refreshLookupStatus() {
  try {
    const s = await fetchLookupStats();
    const knownEl = document.getElementById('lookupKnown');
    const pendEl = document.getElementById('lookupPending');
    if (knownEl) knownEl.textContent = s.known ?? 0;
    if (pendEl) pendEl.textContent = s.pending ?? 0;
  } catch (_) {}
}

function initMap() {
  // Initialize map centered on a default location (will auto-center on first aircraft)
  // Enable touch interactions for iOS/iPad/Safari compatibility
  map = L.map('map', {
    tap: true,  // Enable tap handler for mobile Safari
    tapTolerance: TOUCH_TAP_TOLERANCE,  // Increase tap tolerance for touch devices
    bounceAtZoomLimits: false  // Disable bounce animation that can cause issues on iOS
  }).setView([39.8283, -98.5795], 4); // Center of US as default

  // Use CartoDB dark matter tiles for a sleek look
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
  }).addTo(map);

  // Add label toggle button to map
  const labelToggle = L.control({ position: 'topright' });
  labelToggle.onAdd = function() {
    const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
    div.innerHTML = '<button id="labelToggle" style="background: white; border: none; padding: 8px 12px; cursor: pointer; font-size: 12px; font-weight: 500;">Show Labels</button>';
    div.style.background = 'transparent';
    div.style.border = 'none';
    
    // Prevent map interactions when clicking the button
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);
    
    return div;
  };
  labelToggle.addTo(map);

  // Handle label toggle with click events (Leaflet handles touch->click conversion)
  setTimeout(() => {
    const toggleBtn = document.getElementById('labelToggle');
    const handleToggle = (e) => {
      e.preventDefault();
      e.stopPropagation();
      showLabels = !showLabels;
      toggleBtn.textContent = showLabels ? 'Hide Labels' : 'Show Labels';
      // Update all existing markers
      Object.entries(aircraftMarkers).forEach(([hex, marker]) => {
        if (showLabels && marker.registration) {
          marker.bindTooltip(marker.registration, { permanent: true, direction: 'right', offset: [8, 0], className: 'aircraft-tooltip' }).openTooltip();
        } else {
          marker.unbindTooltip();
        }
      });
    };
    // Single click listener - Leaflet's tap handler converts touch events to clicks
    toggleBtn.addEventListener('click', handleToggle);
  }, 100);
}

function updateMap(aircraft) {
  const currentHexes = new Set();
  
  // Update aircraft count
  const countEl = document.getElementById('aircraftCount');
  if (countEl) {
    countEl.textContent = aircraft.length;
  }
  
  // Update last updated timestamp
  const lastUpdatedEl = document.getElementById('mapLastUpdated');
  if (lastUpdatedEl) {
    const now = new Date();
    lastUpdatedEl.textContent = `Last updated: ${now.toLocaleTimeString()}`;
  }
  
  if (aircraft.length === 0) {
    // Don't clear markers immediately - let stale count handle it
    return;
  }

  // Auto-center on first load if we have aircraft and station location
  if (Object.keys(aircraftMarkers).length === 0 && aircraft.length > 0 && window.stationLocation) {
    const validAircraft = aircraft.filter(a => a.lat && a.lon);
    if (validAircraft.length > 0) {
      const lats = validAircraft.map(a => a.lat);
      const lons = validAircraft.map(a => a.lon);
      
      // Include station in bounds calculation
      lats.push(window.stationLocation.lat);
      lons.push(window.stationLocation.lon);
      
      // Create bounds that include all aircraft and station
      const bounds = [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]];
      
      // Fit bounds to show all aircraft, then set center to station
      map.fitBounds(bounds, { padding: [50, 50] });
      
      // After fitting bounds, set center back to station but keep the zoom level
      const currentZoom = map.getZoom();
      map.setView([window.stationLocation.lat, window.stationLocation.lon], currentZoom);
      console.log('Map centered on station with zoom level:', currentZoom);
    }
  }

  aircraft.forEach(ac => {
    // Skip aircraft without valid coordinates
    if (!ac.lat || !ac.lon || isNaN(ac.lat) || isNaN(ac.lon)) {
      return;
    }
    
    currentHexes.add(ac.hex);
    const rotation = ac.track || 0; // Use track (heading) for rotation
    
    if (aircraftMarkers[ac.hex]) {
      // Update existing marker position and rotation
      aircraftMarkers[ac.hex].setLatLng([ac.lat, ac.lon]);
      aircraftMarkers[ac.hex].staleCount = 0; // Reset stale count
      const el = aircraftMarkers[ac.hex].getElement();
      if (el) {
        const svg = el.querySelector('svg');
        if (svg) {
          svg.style.transform = `rotate(${rotation}deg)`;
        }
      }
    } else {
      // Create new marker as a plane icon (rotation will be applied separately)
      const icon = L.divIcon({
        className: 'aircraft-marker',
        html: `<div style="width:20px;height:20px;"><svg width="16" height="16" viewBox="0 0 20 20" style="transform: rotate(${rotation}deg); transform-origin: center;"><path d="M10 2 L11 7 L16 8 L17 9 L11 10 L11 15 L13 17 L13 18 L10 17 L7 18 L7 17 L9 15 L9 10 L3 9 L4 8 L9 7 L10 2 Z" fill="#3b82f6" stroke="#fff" stroke-width="0.8"/></svg></div>`,
        iconSize: [16, 16],
        iconAnchor: [10, 10]
      });
      
      const marker = L.marker([ac.lat, ac.lon], { 
        icon: icon,
        interactive: true,  // Ensure marker is interactive on touch devices
        bubblingMouseEvents: false  // Prevent event bubbling issues on touch devices
      }).addTo(map);
      marker.registration = ac.registration;
      marker.track = rotation;
      
      // Add click handler for marker - goes to live map page
      // Leaflet automatically handles touch events as clicks
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);  // Prevent map click events
        if (ac.registration) {
          const trimmed = ac.registration.trim().toUpperCase();
          const isFlightNumber = /^[A-Z]{2,3}\d/.test(trimmed);
          let url;
          if (isFlightNumber) {
            const fr24Code = convertToFR24Code(trimmed);
            url = `https://www.flightradar24.com/${fr24Code.toLowerCase()}`;
          } else {
            url = `https://www.flightradar24.com/${trimmed.toLowerCase()}`;
          }
          window.open(url, '_blank');
        }
      });
      
      // Add label if toggle is on
      if (showLabels && ac.registration) {
        marker.bindTooltip(ac.registration, { permanent: true, direction: 'right', offset: [8, 0], className: 'aircraft-tooltip' }).openTooltip();
      }
      
      aircraftMarkers[ac.hex] = marker;
    }
  });

  // Don't remove markers immediately - let the server-side cache handle it
  // Only remove if the aircraft hasn't been in the response for multiple cycles
  Object.keys(aircraftMarkers).forEach(hex => {
    if (!currentHexes.has(hex)) {
      // Mark as stale but don't remove yet
      if (!aircraftMarkers[hex].staleCount) {
        aircraftMarkers[hex].staleCount = 1;
      } else {
        aircraftMarkers[hex].staleCount++;
      }
      
      // Only remove after being stale for 20+ cycles (60 seconds at 3s refresh)
      if (aircraftMarkers[hex].staleCount > 20) {
        map.removeLayer(aircraftMarkers[hex]);
        delete aircraftMarkers[hex];
      }
    } else {
      // Reset stale count if aircraft reappears
      if (aircraftMarkers[hex].staleCount) {
        aircraftMarkers[hex].staleCount = 0;
      }
    }
  });
}

function renderChart(data) {
  const isMobile = window.innerWidth <= 768;
  
  // On mobile, only show top 5
  const displayData = isMobile ? data.slice(0, 5) : data;
  
  const labels = displayData.map(d => d.registration || 'UNKNOWN');
  const counts = displayData.map(d => d.count);
  const ctx = document.getElementById('topChart');
  if (!ctx) return;
  if (chart) chart.destroy();
  
  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ label: 'Top aircraft (tails)', data: counts, maxBarThickness: isMobile ? 50 : 36 }]
    },
    options: { 
      responsive: true,
      indexAxis: 'x', // Always vertical bars now
      maintainAspectRatio: false,
      layout: { padding: { left: isMobile ? 6 : 12, right: isMobile ? 6 : 12 } },
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const label = labels[index];
          const trimmed = label.trim().toUpperCase();
          // Open aircraft data lookup page (not live map)
          const url = `https://www.flightradar24.com/data/aircraft/${trimmed.toLowerCase()}`;
          window.open(url, '_blank');
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true, position: 'nearest' }
      },
      scales: {
        x: { 
          ticks: { 
            color: '#e5e7eb',
            autoSkip: false,
            maxRotation: 45,
            minRotation: 45
          },
          grid: { display: false }
        },
        y: {
          ticks: {
            color: '#e5e7eb',
            stepSize: 1,
            callback: (value) => Number.isInteger(value) ? value : ''
          },
          grid: { color: 'rgba(255, 255, 255, 0.1)' }
        }
      }
    }
  });
}

function renderRecent(rows) {
  const tbody = document.getElementById('recentBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  
  // Show empty state if no rows
  if (rows.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="6" style="text-align: center; padding: 40px; color: #64748b; font-size: 14px;">✈️ No recent sightings available</td>';
    tbody.appendChild(tr);
    return;
  }
  
  for (const r of rows) {
    const tr = document.createElement('tr');
    const t = new Date(r.observed_at * 1000).toLocaleString();
    const tail = r.tail || r.registration || '';
    const trimmed = tail.trim().toUpperCase();
    const isTail = /^N[0-9A-Z]+$|^[A-Z]{2}-?[A-Z0-9]+$/i.test(trimmed);
    // Link to live map page for recent sightings
    const url = tail ? `https://www.flightradar24.com/${trimmed.toLowerCase()}` : '';
    tr.innerHTML = `
      <td>${t}</td>
      <td>${r.hex}</td>
      <td>${tail ? `<a href='${url}' target='_blank' rel='noopener'>${tail}</a>` : ''}</td>
      <td>${r.rssi ?? ''}</td>
      <td>${r.lat ?? ''}</td>
      <td>${r.lon ?? ''}</td>`;
    tbody.appendChild(tr);
  }
}

async function refresh() {
  const top = await fetchTop(currentWindow);
  renderChart(top);
  const recent = await fetchRecent();
  renderRecent(recent);
  
  // Update chart last updated timestamp
  const chartUpdatedEl = document.getElementById('chartLastUpdated');
  if (chartUpdatedEl) {
    const now = new Date();
    chartUpdatedEl.textContent = `Last updated: ${now.toLocaleTimeString()}`;
  }
}

async function refreshMap() {
  const live = await fetchLive();
  updateMap(live);
}

async function refreshStats() {
  const stats = await fetchStats();
  updateStats(stats);
}

document.querySelectorAll('.filters button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentWindow = btn.dataset.window;
    refresh();
  });
});

// Initialize
initMap();
addStationMarker();
initMapToggle();
refresh();
refreshMap();
refreshStats();
refreshLookupStatus();

// Refresh data and map periodically
setInterval(refresh, 15000);
setInterval(refreshMap, 3000); // Update map more frequently for smooth movement
setInterval(refreshStats, 5000); // Update system stats every 5 seconds
setInterval(refreshLookupStatus, 7000); // Update lookup status periodically

async function addStationMarker() {
  try {
    const stationRes = await fetch('/api/station');
    const station = await stationRes.json();
    
    if (station.latitude && station.longitude) {
      // Create a neon green SVG house icon
      const houseIcon = L.divIcon({
        html: `
          <svg width="16" height="16" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <filter id="neon-glow">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <rect x="6" y="12" width="20" height="16" fill="#39ff14" filter="url(#neon-glow)" stroke="#00cc00" stroke-width="1.5" rx="2"/>
            <polygon points="6,12 16,2 26,12" fill="none" stroke="#39ff14" stroke-width="2" stroke-linejoin="round" filter="url(#neon-glow)"/>
            <rect x="14" y="16" width="4" height="8" fill="#00cc00" stroke="#39ff14" stroke-width="1" rx="1"/>
            <circle cx="17.5" cy="20" r="0.8" fill="#39ff14"/>
            <rect x="8" y="14" width="3" height="3" fill="#39ff14" opacity="0.7" rx="0.5"/>
          </svg>
        `,
        iconSize: [16, 16],
        iconAnchor: [8, 16],
        popupAnchor: [0, -16],
        className: 'station-marker'
      });
      
      const stationMarker = L.marker([station.latitude, station.longitude], {
        icon: houseIcon,
        title: station.name
      }).addTo(map);
      
      stationMarker.bindPopup(`<div style="text-align: center; font-weight: bold; color: #39ff14;">${station.name}</div>`);
      
      // Store station location globally for use in updateMap
      window.stationLocation = { lat: station.latitude, lon: station.longitude };
      console.log('Station location loaded:', window.stationLocation);
    }
  } catch (e) {
    console.log('Could not load station marker:', e);
  }
}

function initMapToggle() {
  const mapToggleBtn = document.getElementById('mapToggleBtn');
  const mapSection = document.getElementById('mapSection');
  
  if (!mapToggleBtn || !mapSection) {
    console.log('Map toggle elements not found');
    return;
  }
  
  console.log('initMapToggle: Initializing map toggle button');
  
  // Track whether map is currently shown
  let mapIsShown = false;
  
  // Check screen size and show/hide toggle button
  function checkScreenSize() {
    const isMobile = window.innerWidth <= 480; // Phone-only breakpoint (iPad starts at 768px+)
    console.log('checkScreenSize:', { isMobile, width: window.innerWidth });
    if (isMobile) {
      mapToggleBtn.style.display = 'block';
      // Hide map by default on mobile
      if (!mapIsShown) {
        mapSection.classList.add('hidden-mobile');
        mapToggleBtn.textContent = '📍 Show Map';
      }
    } else {
      mapToggleBtn.style.display = 'none';
      // Always show map on desktop
      mapSection.classList.remove('hidden-mobile');
      mapIsShown = true;
    }
  }
  
  // Toggle map visibility
  function toggleMap() {
    mapIsShown = !mapIsShown;
    console.log('Map toggle:', mapIsShown ? 'showing' : 'hiding');
    
    if (mapIsShown) {
      mapSection.classList.remove('hidden-mobile');
      mapToggleBtn.textContent = '📍 Hide Map';
    } else {
      mapSection.classList.add('hidden-mobile');
      mapToggleBtn.textContent = '📍 Show Map';
    }
  }
  
  // Simple click handler for desktop
  mapToggleBtn.addEventListener('click', toggleMap, false);
  
  // Touch handler - only respond to actual taps on the button itself
  let touchIdentifier = null;
  
  mapToggleBtn.addEventListener('touchstart', (e) => {
    // Only track if this is the first touch
    if (touchIdentifier === null && e.touches.length === 1) {
      touchIdentifier = e.touches[0].identifier;
      console.log('Touch started on button');
    }
  }, { passive: true });
  
  mapToggleBtn.addEventListener('touchend', (e) => {
    // Only respond if this is the same touch that started on the button
    let touchFound = false;
    for (let i = 0; i < e.changedTouches.length; i++) {
      if (e.changedTouches[i].identifier === touchIdentifier) {
        touchFound = true;
        break;
      }
    }
    
    if (touchFound) {
      console.log('Touch ended on button - toggling map');
      e.preventDefault();
      e.stopPropagation();
      toggleMap();
    }
    
    // Reset touch tracking
    touchIdentifier = null;
  }, { passive: false });
  
  mapToggleBtn.addEventListener('touchcancel', (e) => {
    // Reset tracking on cancel
    touchIdentifier = null;
  }, { passive: true });
  
  // Ensure button is interactive on touch devices
  mapToggleBtn.style.webkitTouchCallout = 'none';
  mapToggleBtn.style.webkitUserSelect = 'none';
  mapToggleBtn.style.touchAction = 'manipulation';
  mapToggleBtn.style.cursor = 'pointer';
  mapToggleBtn.style.border = 'none';
  mapToggleBtn.style.outline = 'none';
  
  // Check on load and resize
  checkScreenSize();
  window.addEventListener('resize', checkScreenSize);
}
