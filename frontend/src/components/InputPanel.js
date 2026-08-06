import React, { useCallback, useEffect, useRef, useState } from "react";
import { geoSuggest } from "../services/api";

const MAX_ADDRESSES = 15;
const REPORT_OPTIONS = ["Received", "Not Received", "Rejected/Unreachable"];
const STATUS_OPTIONS = ["Delivered", "Failed"];

export default function InputPanel({
  trafficCondition,
  setTrafficCondition,
  optimization,
  setOptimization,
  demoMode,
  setDemoMode,
  simulationSeed,
  setSimulationSeed,
  loading,
  onSubmit,
  error,
}) {
  const [rows, setRows] = useState([{ id: 1, text: "", lat: null, lng: null, codAmount: "", customerReport: "Received", systemStatus: "Delivered" }]);
  const [formError, setFormError] = useState("");
  const nextId = useRef(2);

  const updateRow = (id, patch) => setRows((current) => current.map((row) => row.id === id ? { ...row, ...patch } : row));
  const addRow = () => {
    if (rows.length >= MAX_ADDRESSES) return;
    setRows((current) => [...current, { id: nextId.current++, text: "", lat: null, lng: null, codAmount: "", customerReport: "Received", systemStatus: "Delivered" }]);
  };
  const removeRow = (id) => setRows((current) => current.length > 1 ? current.filter((row) => row.id !== id) : current);

  const handleSubmit = (event) => {
    event.preventDefault();
    const output = [];
    for (const [index, row] of rows.entries()) {
      const address = row.text.trim();
      if (!address) continue;
      if (!demoMode) {
        const amount = Number(row.codAmount);
        if (!Number.isFinite(amount) || amount < 0) {
          setFormError(`Nominal COD pada alamat #${index + 1} harus berupa angka nol atau lebih.`);
          return;
        }
      }
      output.push({
        address,
        lat: row.lat,
        lng: row.lng,
        adm4_code: row.adm4_code,
        adm2_code: row.adm2_code,
        district: row.district,
        city: row.city,
        county: row.county,
        state: row.state,
        locality: row.locality,
        ...(demoMode ? {} : {
          cod_amount: Number(row.codAmount),
          customer_report: row.customerReport,
          system_status: row.systemStatus,
        }),
      });
    }
    if (!output.length) {
      setFormError("Masukkan minimal satu alamat tujuan.");
      return;
    }
    setFormError("");
    onSubmit(output);
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2"><span aria-hidden="true">📝</span> Input Data Pengiriman</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700" htmlFor="address-1">Masukkan alamat tujuan (ketik untuk melihat saran)</label>
          {rows.map((row, index) => (
            <AddressAutocompleteRow key={row.id} index={index} row={row} loading={loading} demoMode={demoMode} canRemove={rows.length > 1} onChange={(patch) => updateRow(row.id, patch)} onRemove={() => removeRow(row.id)} />
          ))}
          <div className="flex items-center justify-between">
            <button type="button" onClick={addRow} disabled={loading || rows.length >= MAX_ADDRESSES} className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary disabled:opacity-50" aria-label="Tambah alamat tujuan">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded-full bg-primary text-white text-base leading-none" aria-hidden="true">+</span>
              Tambah alamat
            </button>
            <span className="text-xs text-gray-500">{rows.length}/{MAX_ADDRESSES} alamat</span>
          </div>
        </div>

        <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <input type="checkbox" checked={demoMode} onChange={(event) => setDemoMode(event.target.checked)} disabled={loading} />
            Mode Simulasi Demo
          </label>
          {demoMode ? (
            <div className="text-xs text-blue-800">Nominal COD, laporan customer, dan status pengiriman dibuat deterministik oleh backend.</div>
          ) : (
            <div className="text-xs text-blue-800">Mode normal memakai data transaksi yang diisi pada setiap alamat.</div>
          )}
          {demoMode && (
            <label className="flex items-center gap-2 text-sm text-gray-700" htmlFor="simulation-seed">
              Seed simulasi
              <input id="simulation-seed" type="number" min="0" value={simulationSeed} onChange={(event) => setSimulationSeed(Number(event.target.value))} disabled={loading} className="w-28 border border-gray-300 rounded-lg px-2 py-1" />
            </label>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700" htmlFor="traffic-condition">🚦 Kondisi Lalu Lintas:
            <select id="traffic-condition" className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" value={trafficCondition} onChange={(event) => setTrafficCondition(event.target.value)} disabled={loading}>
              <option value="normal">Normal</option><option value="congested">Macet</option><option value="hujan">Hujan</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700" htmlFor="optimization">⚡ Optimasi Rute:
            <select id="optimization" className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" value={optimization} onChange={(event) => setOptimization(event.target.value)} disabled={loading}>
              <option value="distance">Jarak</option><option value="time">ETA / Waktu</option>
            </select>
          </label>
          <button type="submit" disabled={loading} className="ml-auto bg-primary hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-5 py-2.5 rounded-lg transition">
            {loading ? "Memproses..." : "🚀 Jalankan AI & Deteksi Fraud"}
          </button>
        </div>
        {(formError || error) && <div className="bg-red-50 border border-red-300 text-red-700 text-sm rounded-lg p-3" role="alert">⚠️ {formError || error}</div>}
      </form>
    </div>
  );
}

function AddressAutocompleteRow({ index, row, loading, demoMode, canRemove, onChange, onRemove }) {
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [suggestionError, setSuggestionError] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const boxRef = useRef(null);
  const requestRef = useRef(null);
  const timerRef = useRef(null);

  const fetchSuggestions = useCallback(async (text) => {
    requestRef.current?.abort();
    if (!text || text.trim().length < 3) {
      setSuggestions([]); setShowDropdown(false); setFetching(false); return;
    }
    const controller = new AbortController();
    requestRef.current = controller;
    setFetching(true); setSuggestionError("");
    try {
      const response = await geoSuggest(text.trim(), { signal: controller.signal });
      if (!controller.signal.aborted) { setSuggestions(response.results || []); setShowDropdown(true); setActiveIndex(-1); }
    } catch (error) {
      if (!controller.signal.aborted) { setSuggestions([]); setSuggestionError(error.message); }
    } finally {
      if (!controller.signal.aborted) setFetching(false);
    }
  }, []);

  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => fetchSuggestions(row.text), 300);
    return () => { clearTimeout(timerRef.current); requestRef.current?.abort(); };
  }, [row.text, fetchSuggestions]);

  useEffect(() => {
    const onDocumentClick = (event) => { if (boxRef.current && !boxRef.current.contains(event.target)) setShowDropdown(false); };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, []);

  const pick = (suggestion) => {
    onChange({ text: suggestion.label, lat: suggestion.lat, lng: suggestion.lng, adm4_code: suggestion.adm4_code, adm2_code: suggestion.adm2_code, district: suggestion.district, city: suggestion.city, county: suggestion.county, state: suggestion.state, locality: suggestion.locality });
    setShowDropdown(false);
  };

  const onKeyDown = (event) => {
    if (!showDropdown || !suggestions.length) return;
    if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((current) => Math.min(current + 1, suggestions.length - 1)); }
    if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((current) => Math.max(current - 1, 0)); }
    if (event.key === "Enter" && activeIndex >= 0) { event.preventDefault(); pick(suggestions[activeIndex]); }
    if (event.key === "Escape") setShowDropdown(false);
  };

  return (
    <div ref={boxRef} className="relative">
      <div className="flex items-center gap-2">
        <span className="flex-shrink-0 w-6 h-6 inline-flex items-center justify-center rounded-full bg-gray-200 text-gray-600 text-xs font-bold" aria-hidden="true">{index + 1}</span>
        <input id={`address-${index + 1}`} type="text" className="flex-1 p-2.5 border border-gray-300 rounded-lg text-sm" placeholder="Ketik alamat, mis. Jl. Sudirman No.5, Jakarta" value={row.text} onChange={(event) => onChange({ text: event.target.value, lat: null, lng: null, adm4_code: null, adm2_code: null, district: null, city: null, county: null, state: null, locality: null })} onKeyDown={onKeyDown} disabled={loading} autoComplete="off" role="combobox" aria-autocomplete="list" aria-expanded={showDropdown} aria-controls={`suggestions-${index + 1}`} aria-activedescendant={activeIndex >= 0 ? `suggestion-${index + 1}-${activeIndex}` : undefined} />
        {canRemove && <button type="button" onClick={onRemove} disabled={loading} className="flex-shrink-0 w-7 h-7 inline-flex items-center justify-center rounded-full text-gray-400 hover:text-red-600 hover:bg-red-50 text-lg leading-none disabled:opacity-50" aria-label={`Hapus alamat nomor ${index + 1}`}>×</button>}
      </div>
      {!demoMode && (
        <div className="ml-8 mt-2 grid grid-cols-1 md:grid-cols-3 gap-2">
          <input type="number" min="0" step="1000" value={row.codAmount} onChange={(event) => onChange({ codAmount: event.target.value })} disabled={loading} aria-label={`Nominal COD alamat ${index + 1}`} placeholder="Nominal COD" className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm" />
          <select value={row.customerReport} onChange={(event) => onChange({ customerReport: event.target.value })} disabled={loading} aria-label={`Laporan customer alamat ${index + 1}`} className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm">{REPORT_OPTIONS.map((option) => <option key={option}>{option}</option>)}</select>
          <select value={row.systemStatus} onChange={(event) => onChange({ systemStatus: event.target.value })} disabled={loading} aria-label={`Status sistem alamat ${index + 1}`} className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm">{STATUS_OPTIONS.map((option) => <option key={option}>{option}</option>)}</select>
        </div>
      )}
      {showDropdown && (suggestions.length > 0 || suggestionError) && <ul id={`suggestions-${index + 1}`} role="listbox" className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-auto">{suggestions.map((suggestion, suggestionIndex) => <li key={`${suggestion.label}-${suggestionIndex}`} id={`suggestion-${index + 1}-${suggestionIndex}`} role="option" aria-selected={suggestionIndex === activeIndex}><button type="button" onClick={() => pick(suggestion)} className={`w-full text-left px-3 py-2 text-sm ${suggestionIndex === activeIndex ? "bg-blue-50" : "hover:bg-blue-50"}`}><span className="block">{suggestion.label}</span>{suggestion.lat != null && <span className="block text-xs text-gray-400">{suggestion.lat.toFixed(5)}, {suggestion.lng.toFixed(5)}</span>}</button></li>)}{suggestionError && <li className="px-3 py-2 text-xs text-red-600" role="alert">{suggestionError}</li>}</ul>}
      {fetching && <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400" aria-live="polite">mencari…</div>}
      {row.lat != null && <div className="mt-1 pl-8 text-xs text-emerald-600">✓ Lokasi dipilih: {row.lat.toFixed(5)}, {row.lng.toFixed(5)}</div>}
    </div>
  );
}
