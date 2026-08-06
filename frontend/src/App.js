import React, { useRef, useState } from "react";
import InputPanel from "./components/InputPanel";
import MapDisplay from "./components/MapDisplay";
import ResultPanel from "./components/ResultPanel";
import LoadingSpinner from "./components/LoadingSpinner";
import { runSimulation } from "./services/api";

export default function App() {
  const [trafficCondition, setTrafficCondition] = useState("normal");
  const [optimization, setOptimization] = useState("distance");
  const [demoMode, setDemoMode] = useState(true);
  const [simulationSeed, setSimulationSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [routeData, setRouteData] = useState(null);
  const [polyline, setPolyline] = useState("");
  const [etaList, setEtaList] = useState([]);
  const [returnLeg, setReturnLeg] = useState(null);
  const [fraudAlerts, setFraudAlerts] = useState([]);
  const [locations, setLocations] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [simulation, setSimulation] = useState(null);
  const [error, setError] = useState(null);
  const [lastInput, setLastInput] = useState([]);
  const requestController = useRef(null);

  const handleSubmit = async (addressRows) => {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setLoading(true);
    setError(null);
    setLastInput(addressRows);

    try {
      const result = await runSimulation({
        addresses: addressRows,
        trafficCondition,
        optimization,
        demoMode,
        simulationSeed,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setRouteData(result.route);
      setPolyline(result.polyline || "");
      setEtaList(result.eta_list || []);
      setReturnLeg(result.return_leg || null);
      setFraudAlerts(result.fraud_alerts || []);
      setLocations(result.locations || []);
      setWarnings(result.warnings || []);
      setSimulation(result.simulation || null);
    } catch (err) {
      if (err.name !== "AbortError" && !controller.signal.aborted) {
        setError(err.message || "Terjadi kesalahan saat menjalankan simulasi.");
      }
    } finally {
      if (requestController.current === controller) {
        requestController.current = null;
        setLoading(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-primary text-white shadow-md">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <span className="text-3xl" aria-hidden="true">🚚</span>
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
        <InputPanel
          trafficCondition={trafficCondition}
          setTrafficCondition={setTrafficCondition}
          optimization={optimization}
          setOptimization={setOptimization}
          demoMode={demoMode}
          setDemoMode={setDemoMode}
          simulationSeed={simulationSeed}
          setSimulationSeed={setSimulationSeed}
          loading={loading}
          onSubmit={handleSubmit}
          error={error}
        />

        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <span aria-hidden="true">🗺️</span> Peta Rute
          </h2>
          {loading ? (
            <LoadingSpinner message="AI sedang mengoptimasi rute & menganalisis fraud..." />
          ) : routeData ? (
            <MapDisplay
              routeData={routeData}
              polyline={polyline}
              etaList={etaList}
              returnLeg={returnLeg}
              addresses={lastInput}
              locations={locations}
            />
          ) : (
            <div className="h-96 bg-gray-200 rounded-lg flex items-center justify-center text-gray-500 text-sm">
              Jalankan simulasi untuk menampilkan peta rute
            </div>
          )}
          {routeData && (
            <p className="mt-2 text-xs text-gray-500">
              Klik marker untuk melihat alamat, ETA, dan cuaca.
            </p>
          )}
        </div>

        <ResultPanel
          etaList={etaList}
          returnLeg={returnLeg}
          fraudAlerts={fraudAlerts}
          addresses={lastInput}
          locations={locations}
          warnings={warnings}
          simulation={simulation}
        />
      </main>

      <footer className="text-center text-xs text-gray-400 py-6">
        Compfest18 — COMPFEST 18 AIC · XGBoost Fraud + OR-Tools Routing + FastAPI
      </footer>
    </div>
  );
}
