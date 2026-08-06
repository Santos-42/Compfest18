import React, { useState, useRef, useCallback, useEffect } from "react";
import { geoSuggest } from "../services/api";

/**
 * InputPanel — daftar input alamat dinamis ala Google Maps:
 * autocomplete per baris + tombol "+" tambah alamat + tombol hapus.
 */
export default function InputPanel({
  addresses,
  setAddresses,
  trafficCondition,
  setTrafficCondition,
  optimization,
  setOptimization,
  loading,
  onSubmit,
  error,
}) {
  const [rows, setRows] = useState([{ text: "", lat: null, lng: null }]);

  const handleAdd = () => {
    setRows((prev) => [...prev, { text: "", lat: null, lng: null }]);
  };

  const handleRemove = (idx) => {
    setRows((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev));
  };

  const handleChange = (idx, patch) => {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const valid = rows
      .map((r) => ({
        address: r.text.trim(),
        lat: r.lat,
        lng: r.lng,
      }))
      .filter((r) => r.address);
    if (valid.length === 0) {
      alert("Masukkan minimal 1 alamat tujuan.");
      return;
    }
    onSubmit(valid);
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
        <span>📝</span> Input Data Pengiriman
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Masukkan alamat tujuan (ketik untuk melihat saran)
          </label>
          {rows.map((row, idx) => (
            <AddressAutocompleteRow
              key={idx}
              index={idx}
              row={row}
              canRemove={rows.length > 1}
              onChange={(patch) => handleChange(idx, patch)}
              onRemove={() => handleRemove(idx)}
            />
          ))}
          <button
            type="button"
            onClick={handleAdd}
            className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-blue-700"
          >
            <span className="w-5 h-5 inline-flex items-center justify-center rounded-full bg-primary text-white text-base leading-none">
              +
            </span>
            Tambah alamat
          </button>
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

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">⚡ Optimasi Rute:</span>
            <select
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={optimization}
              onChange={(e) => setOptimization(e.target.value)}
              disabled={loading}
            >
              <option value="distance">Jarak</option>
              <option value="time">ETA / Waktu</option>
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

/**
 * AddressAutocompleteRow — satu baris input alamat dengan dropdown saran.
 */
function AddressAutocompleteRow({ index, row, canRemove, onChange, onRemove }) {
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [fetching, setFetching] = useState(false);
  const timerRef = useRef(null);
  const boxRef = useRef(null);
  const suppressRef = useRef(false);

  // Debounce fetch saran saat mengetik
  const fetchSuggestions = useCallback(async (text) => {
    if (suppressRef.current) {
      suppressRef.current = false;
      return;
    }
    if (!text || text.trim().length < 3) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }
    setFetching(true);
    try {
      const res = await geoSuggest(text.trim());
      setSuggestions(res.results || []);
      setShowDropdown(true);
    } catch (_) {
      setSuggestions([]);
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => fetchSuggestions(row.text), 300);
    return () => clearTimeout(timerRef.current);
  }, [row.text, fetchSuggestions]);

  // Tutup dropdown saat klik di luar
  useEffect(() => {
    function onDocClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const pickSuggestion = (s) => {
    suppressRef.current = true; // cegah fetch ulang setelah pilih
    onChange({ text: s.label, lat: s.lat, lng: s.lng });
    setShowDropdown(false);
  };

  return (
    <div ref={boxRef} className="relative">
      <div className="flex items-center gap-2">
        <span className="flex-shrink-0 w-6 h-6 inline-flex items-center justify-center rounded-full bg-gray-200 text-gray-600 text-xs font-bold">
          {index + 1}
        </span>
        <input
          type="text"
          className="flex-1 p-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="Ketik alamat, mis. Jl. Sudirman No.5, Jakarta"
          value={row.text}
          onChange={(e) => onChange({ text: e.target.value, lat: null, lng: null })}
          disabled={false}
          autoComplete="off"
        />
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="flex-shrink-0 w-7 h-7 inline-flex items-center justify-center rounded-full text-gray-400 hover:text-red-600 hover:bg-red-50 text-lg leading-none"
            title="Hapus alamat"
          >
            ×
          </button>
        )}
      </div>

      {showDropdown && suggestions.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-auto">
          {suggestions.map((s, i) => (
            <li key={i}>
              <button
                type="button"
                onClick={() => pickSuggestion(s)}
                className="w-full text-left px-3 py-2 text-sm hover:bg-blue-50"
              >
                <span className="block">{s.label}</span>
                {s.lat != null && (
                  <span className="block text-xs text-gray-400">
                    {s.lat.toFixed(5)}, {s.lng.toFixed(5)}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      {fetching && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">
          mencari…
        </div>
      )}

      {row.lat != null && (
        <div className="mt-1 pl-8 text-xs text-emerald-600">
          ✓ Lokasi dipilih: {row.lat.toFixed(5)}, {row.lng.toFixed(5)}
        </div>
      )}
    </div>
  );
}
