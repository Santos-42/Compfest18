import React from "react";

/**
 * ResultPanel — Tabel Rute & ETA + Kartu Deteksi Fraud (merah/hijau).
 * props: etaList (array), fraudAlerts (array)
 */
export default function ResultPanel({ etaList, fraudAlerts, addresses }) {
  const hasData = etaList && etaList.length > 0;

  return (
    <div className="space-y-6">
      {/* ===== Tabel Rute & ETA ===== */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span>📋</span> Tabel Rute & ETA
        </h2>
        {!hasData ? (
          <p className="text-sm text-gray-500">
            Belum ada simulasi. Jalankan AI untuk melihat hasil.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-200 text-gray-600">
                  <th className="py-2 pr-4">No</th>
                  <th className="py-2 pr-4">Alamat</th>
                  <th className="py-2 pr-4">ETA</th>
                  <th className="py-2">Cuaca</th>
                </tr>
              </thead>
              <tbody>
                {etaList.map((eta, idx) => (
                  <tr key={idx} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-semibold">{eta.stop}</td>
                    <td className="py-2 pr-4">
                      {addresses && addresses[eta.order_index - 1]
                        ? addresses[eta.order_index - 1]
                        : `Stop #${eta.stop}`}
                    </td>
                    <td className="py-2 pr-4 font-mono">{eta.eta}</td>
                    <td className="py-2">
                      {eta.weather || "Cerah"} {eta.temperature ? `(${eta.temperature}°C)` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ===== Kartu Deteksi Fraud ===== */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span>🚨</span> Deteksi Fraud (AI)
        </h2>

        {!hasData ? (
          <p className="text-sm text-gray-500">
            Belum ada hasil analisis.
          </p>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {fraudAlerts && fraudAlerts.length > 0 ? (
              fraudAlerts.map((alert, idx) => (
                <FraudCard key={idx} alert={alert} addresses={addresses} />
              ))
            ) : (
              <p className="text-sm text-gray-500">
                Tidak ada order berisiko.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function FraudCard({ alert, addresses }) {
  const isFraud = alert.status === "fraud";
  return (
    <div
      className={`rounded-xl border p-4 ${
        isFraud
          ? "bg-red-50 border-red-300"
          : "bg-green-50 border-green-200"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${
              isFraud
                ? "bg-red-600 text-white"
                : "bg-green-600 text-white"
            }`}
          >
            {isFraud ? "🚨 FRAUD" : "✅ AMAN"}
          </span>
          <span className="text-sm font-semibold text-gray-700">
            Order #{alert.order_index}
          </span>
        </div>
        <span className="text-xs text-gray-500 font-mono">
          Skor AI: {(alert.score * 100).toFixed(0)}%
        </span>
      </div>

      <div className="mt-3 text-sm text-gray-700 space-y-1">
        <p>
          📦 Alamat:{" "}
          {addresses && addresses[alert.order_index - 1]
            ? addresses[alert.order_index - 1]
            : alert.address}
        </p>
        <p>
          💰 COD: Rp{" "}
          {Number(alert.cod_amount || 0).toLocaleString("id-ID")}
        </p>
        <p>📍 Jarak GPS: {alert.gps_distance_m} m</p>
        <p>📋 Laporan Customer: {alert.customer_report}</p>
      </div>

      {isFraud && (
        <div className="mt-3 space-y-2">
          <div className="bg-red-100 border border-red-300 rounded-lg p-3 text-sm text-red-800">
            💬 {alert.reason || "Fraud terdeteksi berdasarkan anomali data."}
          </div>
          <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-sm text-amber-800">
            ✅ Rekomendasi:{" "}
            {alert.recommendation || "Freeze Settlement & Investigasi Kurir"}
          </div>
        </div>
      )}
    </div>
  );
}
