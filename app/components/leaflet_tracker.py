from __future__ import annotations

from collections.abc import Iterable
import math
import pandas as pd
import streamlit as st

_HTML = '<div id="fleet-leaflet-map" role="application" aria-label="Live equipment tracking map"></div>'
_CSS = """
#fleet-leaflet-map { height: 520px; width: 100%; border-radius: 14px; overflow: hidden; background: #0c1728; }
.leaflet-popup-content-wrapper, .leaflet-popup-tip { background: #102039; color: #e6eefb; }
.fleet-popup h4 { margin: 0 0 6px; font: 700 14px system-ui; color: #5eead4; }
.fleet-popup p { margin: 3px 0; font: 12px system-ui; color: #c9d7e8; }
.fleet-marker { border-radius: 50%; width: 18px; height: 18px; border: 3px solid #fff; box-shadow: 0 0 0 3px rgba(8,17,31,.55), 0 3px 9px rgba(0,0,0,.45); }
.fleet-marker.critical { background: #fb7185; }.fleet-marker.warning { background: #fbbf24; }.fleet-marker.normal { background: #5eead4; }
"""
_JS = """
const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
const LEAFLET_JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) {
    const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = LEAFLET_CSS; document.head.appendChild(link);
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${LEAFLET_JS}"]`);
    if (existing) { existing.addEventListener('load', () => resolve(window.L), {once:true}); existing.addEventListener('error', reject, {once:true}); return; }
    const script = document.createElement('script'); script.src = LEAFLET_JS; script.onload = () => resolve(window.L); script.onerror = reject; document.head.appendChild(script);
  });
}
function textElement(tag, text) { const el = document.createElement(tag); el.textContent = text || '—'; return el; }
export default function(component) {
  const { data, parentElement } = component;
  const root = parentElement.querySelector('#fleet-leaflet-map');
  if (!root) return;
  loadLeaflet().then(L => {
    if (root._fleetMap) { root._fleetMap.remove(); root._fleetMap = null; }
    const map = L.map(root, { zoomControl: true, scrollWheelZoom: true }).setView(data.center || [20.5937, 78.9629], data.zoom || 5);
    root._fleetMap = map;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
    const bounds = [];
    (data.tracks || []).forEach(track => {
      if (!track.points || track.points.length < 2) return;
      const points = track.points.map(point => [point.lat, point.lon]);
      L.polyline(points, { color: track.color || '#60a5fa', weight: 3, opacity: .72 }).addTo(map);
      points.forEach(point => bounds.push(point));
    });
    (data.assets || []).forEach(asset => {
      if (!Number.isFinite(asset.lat) || !Number.isFinite(asset.lon)) return;
      const icon = L.divIcon({ className: '', html: `<div class="fleet-marker ${asset.level || 'normal'}"></div>`, iconSize: [18,18], iconAnchor: [9,9] });
      const marker = L.marker([asset.lat, asset.lon], {icon}).addTo(map);
      const popup = document.createElement('div'); popup.className = 'fleet-popup';
      popup.appendChild(textElement('h4', asset.equipment_id));
      popup.appendChild(textElement('p', `${asset.equipment_type || 'Equipment'} · ${asset.status || 'Unknown'}`));
      popup.appendChild(textElement('p', `Health ${asset.health ?? '—'} · Fuel ${asset.fuel ?? '—'}%`));
      popup.appendChild(textElement('p', `Temp ${asset.temperature ?? '—'}°C · ${asset.geofence || 'Unknown'} geofence`));
      popup.appendChild(textElement('p', `Last signal ${asset.timestamp || '—'}`));
      marker.bindPopup(popup);
      bounds.push([asset.lat, asset.lon]);
    });
    if (bounds.length) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 12 });
    else map.setView(data.center || [20.5937, 78.9629], data.zoom || 5);
  }).catch(() => { root.innerHTML = '<p style="padding:20px;color:#fda4af">Unable to load Leaflet map resources. Check network access to Leaflet and OpenStreetMap.</p>'; });
  return () => { if (root && root._fleetMap) root._fleetMap.remove(); };
}
"""

_MAP = st.components.v2.component("fleetsight_leaflet_live_tracker", html=_HTML, css=_CSS, js=_JS)


def _number(value) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def render_live_tracker(assets: pd.DataFrame, telemetry: pd.DataFrame, *, key: str = "fleet-live-tracker") -> None:
    """Render markers for latest equipment points and efficient recent track lines."""
    asset_payload = []
    for row in assets.dropna(subset=["gps_lat", "gps_lon"]).to_dict("records"):
        alert = str(row.get("severity", "")).lower()
        level = "critical" if alert == "critical" or str(row.get("geofence_status", "")).lower() == "outside" else "warning" if alert == "warning" else "normal"
        asset_payload.append({"equipment_id": str(row.get("equipment_id")), "equipment_type": str(row.get("equipment_type", "")), "status": str(row.get("current_status", "")), "health": round(_number(row.get("condition_score")) or 0), "fuel": round(_number(row.get("fuel_level_percent")) or 0), "temperature": round(_number(row.get("engine_temperature_c")) or 0, 1), "geofence": str(row.get("geofence_status", "")), "timestamp": str(row.get("timestamp", ""))[:16], "lat": _number(row.get("gps_lat")), "lon": _number(row.get("gps_lon")), "level": level})
    tracked_ids = [asset["equipment_id"] for asset in asset_payload[:20]]
    history = telemetry[telemetry.equipment_id.isin(tracked_ids)].copy()
    history["timestamp"] = pd.to_datetime(history.timestamp, errors="coerce")
    history = history.dropna(subset=["gps_lat", "gps_lon", "timestamp"]).sort_values("timestamp").groupby("equipment_id").tail(25)
    tracks = []
    for index, (equipment_id, group) in enumerate(history.groupby("equipment_id")):
        tracks.append({"equipment_id": equipment_id, "color": ["#60a5fa", "#a78bfa", "#fbbf24", "#5eead4"][index % 4], "points": [{"lat": _number(row.gps_lat), "lon": _number(row.gps_lon)} for _, row in group.iterrows()]})
    _MAP(data={"assets": asset_payload, "tracks": tracks, "center": [20.5937, 78.9629], "zoom": 5}, key=key, height=540)
