import React, { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { buildRouteMarkers, decodePolyline } from "./mapUtils";

export default function MapDisplay({ routeData, polyline, etaList, returnLeg, addresses, locations }) {
  const coordinates = routeData?.coordinates || [];
  const routeOrder = routeData?.order || [];
  const decoded = useMemo(() => decodePolyline(polyline), [polyline]);
  const markers = buildRouteMarkers(routeOrder, coordinates, etaList, addresses, locations);
  const orderedPositions = routeOrder
    .map((index) => coordinates[index])
    .filter(Boolean)
    .map(([lng, lat]) => [lat, lng]);
  const center = orderedPositions[0] || [-6.2, 106.816666];

  return (
    <div className="space-y-2" aria-label="Peta rute pengiriman">
      <MapContainer center={center} zoom={12} style={{ height: 384, width: "100%" }} className="rounded-lg z-0">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds positions={orderedPositions} />
        {decoded.length > 1 && (
          <Polyline positions={decoded} pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.8 }} />
        )}
        {markers.map((marker) => (
          <Marker
            key={`${marker.nodeIndex}-${marker.routePosition}`}
            position={marker.position}
            icon={marker.isOrigin ? greenIcon() : redIcon(marker.label)}
          >
            <Popup>
              {marker.isOrigin ? (
                <b>🟢 Gudang / Origin</b>
              ) : (
                <div>
                  <b>Stop #{marker.label}</b>
                  <div className="text-sm text-gray-700 mt-0.5">📍 {marker.address || "Alamat tidak tersedia"}</div>
                  {marker.eta && (
                    <div className="text-sm text-gray-700">
                      ETA: {marker.eta.eta} ({marker.eta.eta_date}) — {marker.eta.weather}
                      {marker.eta.temperature != null ? ` (${marker.eta.temperature}°C)` : ""}
                    </div>
                  )}
                  {marker.location?.source && (
                    <div className="text-xs text-gray-500">Sumber lokasi: {marker.location.source}</div>
                  )}
                </div>
              )}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {routeData?.closed && (
        <p className="text-xs text-gray-500">
          Rute tertutup: kendaraan kembali ke gudang setelah stop terakhir
          {returnLeg?.eta ? ` pada ${returnLeg.eta} (${returnLeg.eta_date}).` : "."}
        </p>
      )}
      {routeData?.total_distance_m != null && (
        <p className="text-xs text-gray-500">
          Total rute: {(routeData.total_distance_m / 1000).toFixed(1)} km
        </p>
      )}
    </div>
  );
}

function FitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 1) map.fitBounds(positions, { padding: [24, 24] });
  }, [map, positions]);
  return null;
}

function greenIcon() {
  return L.divIcon({
    className: "",
    html: '<div style="width:16px;height:16px;background:#16a34a;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
    iconSize: [16, 16],
  });
}

function redIcon(number) {
  const safeNumber = Number.isFinite(Number(number)) ? Number(number) : "?";
  return L.divIcon({
    className: "",
    html: `<div style="width:22px;height:22px;background:#dc2626;color:white;font-size:11px;font-weight:bold;display:flex;align-items:center;justify-content:center;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.4)">${safeNumber}</div>`,
    iconSize: [22, 22],
  });
}
