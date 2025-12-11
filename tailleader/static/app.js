let currentWindow = '24h';
let chart;
let map;
let aircraftMarkers = {};
let showLabels = false;

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
  map = L.map('map').setView([39.8283, -98.5795], 4); // Center of US as default

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
    return div;
  };
  labelToggle.addTo(map);

  // Handle label toggle
  setTimeout(() => {
    document.getElementById('labelToggle').addEventListener('click', () => {
      showLabels = !showLabels;
      document.getElementById('labelToggle').textContent = showLabels ? 'Hide Labels' : 'Show Labels';
      // Update all existing markers
      Object.entries(aircraftMarkers).forEach(([hex, marker]) => {
        if (showLabels && marker.registration) {
          marker.bindTooltip(marker.registration, { permanent: true, direction: 'right', offset: [8, 0], className: 'aircraft-tooltip' }).openTooltip();
        } else {
          marker.unbindTooltip();
        }
      });
    });
  }, 100);
}

function updateMap(aircraft) {
  const currentHexes = new Set();
  
  if (aircraft.length === 0) {
    // Don't clear markers immediately - let stale count handle it
    return;
  }

  // Auto-center on first load if we have aircraft
  if (Object.keys(aircraftMarkers).length === 0 && aircraft.length > 0) {
    const validAircraft = aircraft.filter(a => a.lat && a.lon);
    if (validAircraft.length > 0) {
      const lats = validAircraft.map(a => a.lat);
      const lons = validAircraft.map(a => a.lon);
      const bounds = [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]];
      map.fitBounds(bounds, { padding: [50, 50] });
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
        html: `<div style="width:20px;height:20px;"><svg width="20" height="20" viewBox="0 0 20 20" style="transform: rotate(${rotation}deg); transform-origin: center;"><path d="M10 2 L11 7 L16 8 L17 9 L11 10 L11 15 L13 17 L13 18 L10 17 L7 18 L7 17 L9 15 L9 10 L3 9 L4 8 L9 7 L10 2 Z" fill="#3b82f6" stroke="#fff" stroke-width="0.8"/></svg></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });
      
      const marker = L.marker([ac.lat, ac.lon], { icon: icon }).addTo(map);
      marker.registration = ac.registration;
      marker.track = rotation;
      
      // Add click handler for marker - goes to live map page
      marker.on('click', () => {
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
refresh();
refreshMap();
refreshStats();
refreshLookupStatus();

// Refresh data and map periodically
setInterval(refresh, 15000);
setInterval(refreshMap, 3000); // Update map more frequently for smooth movement
setInterval(refreshStats, 5000); // Update system stats every 5 seconds
setInterval(refreshLookupStatus, 7000); // Update lookup status periodically
