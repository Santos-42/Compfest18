import React, { useState } from "react";
import InputPanel from "./components/InputPanel";
import MapDisplay from "./components/MapDisplay";
import ResultPanel from "./components/ResultPanel";
import LoadingSpinner from "./components/LoadingSpinner";
import { runSimulation } from "./services/api";

/**
 * App — container utama 1 halaman. Kelola semua state.
 */
export default function App() {
  const [trafficCondition, setTrafficCondition] = useState("normal");
  const [optimization, setOptimization] = useState("distance");
  const [loading, setLoading] = useState(false);
  const [routeData, setRouteData] = useState(null); // { polyline, markers }
  const [polyline, setPolyline] = useState("");
  const [etaList, setEtaList] = useState([]);
  const [fraudAlerts, setFraudAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [lastInput, setLastInput] = useState([]);

  const handleSubmit = async (addressRows) => {
    setLoading(true);
    setError(null);
    setRouteData(null);
    setPolyline("");
    setEtaList([]);
    setFraudAlerts([]);
    setLastInput(addressRows);

    try {
      const result = await runSimulation({
        addresses: addressRows, // [{ address, lat, lng }, ...]
        codAmounts: null, // backend generate otomatis
        trafficCondition,
        optimization,
      });
      setRouteData(result.route);
      setPolyline(result.polyline);
      setEtaList(result.eta_list || []);
      setFraudAlerts(result.fraud_alerts || []);
    } catch (err) {
      setError(err.message || "Terjadi kesalahan saat menjalankan simulasi.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-primary text-white shadow-md">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <span className="text-3xl">🚚</span>
          <div>
            <h1 className="text-xl font-bold leading-tight">
              Compfest18 — Smart Logistics Simulator
            </h1>
            <p className="text-sm text-blue-100">
              Optimasi Rute + Deteksi Fraud COD berbasis AI
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Block 1: Input */}
        <InputPanel
          trafficCondition={trafficCondition}
          setTrafficCondition={setTrafficCondition}
          optimization={optimization}
          setOptimization={setOptimization}
          loading={loading}
          onSubmit={handleSubmit}
          error={error}
        />

        {/* Block 2: Peta */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <span>🗺️</span> Peta Rute
          </h2>
          {loading ? (
            <LoadingSpinner message="AI sedang mengoptimasi rute & menganalisis fraud..." />
          ) : routeData ? (
            <MapDisplay
              routeData={routeData}
              polyline={polyline}
              etaList={etaList}
              addresses={lastInput}
            />
          ) : (
            <div className="h-96 bg-gray-200 rounded-lg flex items-center justify-center text-gray-500 text-sm">
              Jalankan simulasi untuk menampilkan peta rute
            </div>
          )}
          {routeData && (
            <p className="mt-2 text-xs text-gray-500">
              * Klik marker untuk melihat ETA & cuaca
            </p>
          )}
        </div>

        {/* Block 3: Hasil */}
        <ResultPanel
          etaList={etaList}
          fraudAlerts={fraudAlerts}
          addresses={lastInput}
        />
      </main>

      <footer className="text-center text-xs text-gray-400 py-6">
        Compfest18 — COMPFEST 18 AIC · XGBoost + OR-Tools + FastAPI
      </footer>
    </div>
  );
}
