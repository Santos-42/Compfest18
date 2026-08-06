import React, { useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
} from "react-leaflet";
import L from "leaflet";

/**
 * MapDisplay — peta Leaflet dengan marker & polyline rute.
 * routeData: { order, coordinates } (coordinates: [lng, lat])
 * polyline: encoded polyline5 dari backend (opsional, dipakai jika ada)
 * etaList: [{ stop, order_index, eta, weather, temperature }]
 * addresses: array objek { address, lat, lng } urut input user
 */
export default function MapDisplay({ routeData, polyline, etaList, addresses }) {
  const coords = routeData?.coordinates || [];

  const decoded = useMemo(() => decodePolyline(polyline), [polyline]);

  // Posisi marker: coords[0] = origin, coords[1..] = titik kunjungan.
  // Label marker = nomor STOP kunjungan (dari etaList), bukan indeks fisik,
  // agar konsisten dengan Tabel Rute & ETA.
  const markers = coords.map(([lng, lat], idx) => {
    const eta = etaList && etaList[idx - 1] ? etaList[idx - 1] : null;
    const orderIdx = eta ? eta.order_index : idx;
    const stopLabel = eta ? eta.stop : idx; // nomor urutan kunjungan
    const addrObj = addresses && addresses[orderIdx - 1];
    const addressLabel =
      addrObj && typeof addrObj === "object" ? addrObj.address : null;
    return {
      position: [lat, lng],
      isOrigin: idx === 0,
      label: String(stopLabel),
      eta,
      address: addressLabel,
    };
  });

  const center = coords.length
    ? [coords[0][1], coords[0][0]]
    : [-6.2, 106.816666];

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: 384, width: "100%" }}
      className="rounded-lg z-0"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {decoded.length > 1 && (
        <Polyline
          positions={decoded}
          pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.8 }}
        />
      )}
      {markers.map((m, i) => (
        <Marker
          key={i}
          position={m.position}
          icon={m.isOrigin ? greenIcon() : redIcon(m.label)}
        >
          <Popup>
            {m.isOrigin ? (
              <b>🟢 Origin (Gudang)</b>
            ) : (
              <div>
                <b>Stop #{m.label}</b>
                {m.address && (
                  <div className="text-sm text-gray-700 mt-0.5">
                    📍 {m.address}
                  </div>
                )}
                {m.eta && (
                  <div className="text-sm text-gray-700">
                    ETA: {m.eta.eta} — {m.eta.weather}
                    {m.eta.temperature ? ` (${m.eta.temperature}°C)` : ""}
                  </div>
                )}
              </div>
            )}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

function greenIcon() {
  return L.divIcon({
    className: "",
    html: '<div style="width:16px;height:16px;background:#16a34a;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
    iconSize: [16, 16],
  });
}

function redIcon(num) {
  return L.divIcon({
    className: "",
    html: `<div style="width:22px;height:22px;background:#dc2626;color:white;font-size:11px;font-weight:bold;display:flex;align-items:center;justify-content:center;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.4)">${num}</div>`,
    iconSize: [22, 22],
  });
}

function decodePolyline(str) {
  if (!str) return [];
  let index = 0,
    lat = 0,
    lng = 0,
    coordinates = [];
  while (index < str.length) {
    let result = 0,
      shift = 0,
      b;
    do {
      b = str.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;

    result = 0;
    shift = 0;
    do {
      b = str.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;

    coordinates.push([lat / 1e5, lng / 1e5]);
  }
  return coordinates;
}
