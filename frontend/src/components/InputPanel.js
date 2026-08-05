import React from "react";

/**
 * InputPanel — textarea alamat + dropdown kondisi lalu lintas + tombol jalankan.
 */
export default function InputPanel({
  addresses,
  setAddresses,
  trafficCondition,
  setTrafficCondition,
  loading,
  onSubmit,
  error,
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    const lines = addresses
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (lines.length === 0) {
      alert("Masukkan minimal 1 alamat tujuan.");
      return;
    }
    onSubmit(lines);
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
        <span>📝</span> Input Data Pengiriman
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Masukkan alamat tujuan (1 per baris, format: alamat, kota)
          </label>
          <textarea
            className="w-full h-32 p-3 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder={
              "Jl. Sudirman No.5, Jakarta\nJl. Gatot Subroto No.10, Jakarta\nJl. Thamrin No.15, Jakarta"
            }
            value={addresses}
            onChange={(e) => setAddresses(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">🚦 Kondisi Lalu Lintas:</span>
            <select
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={trafficCondition}
              onChange={(e) => setTrafficCondition(e.target.value)}
              disabled={loading}
            >
              <option value="normal">Normal</option>
              <option value="congested">Macet</option>
              <option value="hujan">Hujan</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="ml-auto bg-primary hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-5 py-2.5 rounded-lg transition"
          >
            {loading ? "Memproses..." : "🚀 Jalankan AI & Deteksi Fraud"}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-300 text-red-700 text-sm rounded-lg p-3">
            ⚠️ {error}
          </div>
        )}
      </form>
    </div>
  );
}
