import React from "react";

export default function ResultPanel({ etaList, returnLeg, fraudAlerts, addresses, locations, warnings, simulation }) {
  const hasData = etaList?.length > 0;
  return (
    <div className="space-y-6">
      {(simulation?.demo_mode || warnings?.length > 0) && (
        <div className="bg-amber-50 border border-amber-300 text-amber-900 rounded-xl p-4 text-sm" role="status">
          {simulation?.demo_mode && <p className="font-semibold">Mode Simulasi — seed {simulation.seed}</p>}
          {warnings?.map((warning) => <p key={warning}>⚠️ {warning}</p>)}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span aria-hidden="true">📋</span> Tabel Rute & ETA
        </h2>
        {!hasData ? (
          <p className="text-sm text-gray-500">Belum ada simulasi. Jalankan AI untuk melihat hasil.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Urutan pengiriman dan perkiraan waktu tiba</caption>
              <thead>
                <tr className="text-left border-b border-gray-200 text-gray-600">
                  <th scope="col" className="py-2 pr-4">No</th>
                  <th scope="col" className="py-2 pr-4">Alamat</th>
                  <th scope="col" className="py-2 pr-4">ETA</th>
                  <th scope="col" className="py-2 pr-4">Jarak Kumulatif</th>
                  <th scope="col" className="py-2">Cuaca</th>
                </tr>
              </thead>
              <tbody>
                {etaList.map((eta) => (
                  <tr key={eta.order_index} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-semibold">{eta.stop}</td>
                    <td className="py-2 pr-4">{addressFor(eta.order_index, addresses, eta.address)}</td>
                    <td className="py-2 pr-4 font-mono">{eta.eta} ({eta.eta_date})</td>
                    <td className="py-2 pr-4 font-mono">{formatDistance(eta.cumulative_distance_m)}</td>
                    <td className="py-2">{eta.weather || "Tidak tersedia"} {eta.temperature != null ? `(${eta.temperature}°C)` : ""}</td>
                  </tr>
                ))}
                {returnLeg && (
                  <tr className="border-t-2 border-blue-100 bg-blue-50">
                    <td className="py-2 pr-4 font-semibold">↩</td>
                    <td className="py-2 pr-4">Kembali ke Gudang</td>
                    <td className="py-2 pr-4 font-mono">{returnLeg.eta} ({returnLeg.eta_date})</td>
                    <td className="py-2 pr-4 font-mono">{formatDistance(returnLeg.cumulative_distance_m)}</td>
                    <td className="py-2">{returnLeg.weather || "Tidak tersedia"}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span aria-hidden="true">🚨</span> Deteksi Fraud (AI)
        </h2>
        {!hasData ? (
          <p className="text-sm text-gray-500">Belum ada hasil analisis.</p>
        ) : fraudAlerts?.length > 0 ? (
          <div className="grid md:grid-cols-2 gap-4">
            {fraudAlerts.map((alert) => <FraudCard key={alert.order_index} alert={alert} addresses={addresses} locations={locations} />)}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Tidak ada order berisiko.</p>
        )}
      </div>
    </div>
  );
}

function FraudCard({ alert, addresses, locations }) {
  const isFraud = alert.status === "fraud";
  const score = Number(alert.score);
  const scoreLabel = Number.isFinite(score) ? `${(score * 100).toFixed(0)}%` : "Tidak tersedia";
  const codLabel = Number.isFinite(Number(alert.cod_amount)) ? `Rp ${Number(alert.cod_amount).toLocaleString("id-ID")}` : "Tidak tersedia";
  return (
    <div className={`rounded-xl border p-4 ${isFraud ? "bg-red-50 border-red-300" : "bg-green-50 border-green-200"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${isFraud ? "bg-red-600 text-white" : "bg-green-600 text-white"}`}>
            {isFraud ? "🚨 FRAUD" : "✅ AMAN"}
          </span>
          <span className="text-sm font-semibold text-gray-700">Order #{alert.order_index}</span>
        </div>
        <span className="text-xs text-gray-500 font-mono">Skor AI: {scoreLabel}</span>
      </div>
      <div className="mt-3 text-sm text-gray-700 space-y-1">
        <p>📦 Alamat: {addressFor(alert.order_index, addresses, alert.address)}</p>
        <p>💰 COD: {codLabel}</p>
        <p>📍 Jarak GPS: {alert.gps_distance_m ?? "Tidak tersedia"} m</p>
        <p>📋 Laporan Customer: {alert.customer_report || "Tidak tersedia"}</p>
        <p>🚚 Status Sistem: {alert.system_status || "Tidak tersedia"}</p>
        {locations?.[alert.order_index - 1]?.source && <p>🧭 Sumber lokasi: {locations[alert.order_index - 1].source}</p>}
      </div>
      {isFraud && (
        <div className="mt-3 space-y-2">
          <div className="bg-red-100 border border-red-300 rounded-lg p-3 text-sm text-red-800">💬 {alert.reason || "Fraud terdeteksi berdasarkan anomali data."}</div>
          <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-sm text-amber-800">✅ Rekomendasi: {alert.recommendation || "Freeze Settlement & Investigasi Kurir"}</div>
        </div>
      )}
    </div>
  );
}

function addressFor(orderIndex, addresses, fallback) {
  const value = addresses?.[orderIndex - 1];
  if (typeof value === "string") return value;
  return value?.address || fallback || `Stop #${orderIndex}`;
}

function formatDistance(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) / 1000).toFixed(1)} km` : "-";
}
