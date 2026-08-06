const API_BASE = process.env.REACT_APP_API_URL || "";

function endpoint(path) {
  return `${API_BASE}${path}`;
}

async function fetchJson(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 30000);
  const externalSignal = options.signal;
  const abortExternal = () => controller.abort();
  externalSignal?.addEventListener("abort", abortExternal, { once: true });
  try {
    const response = await fetch(endpoint(path), {
      ...options,
      signal: controller.signal,
    });
    let data = null;
    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }
    if (!response.ok) {
      const detail = data?.detail;
      const message = typeof detail === "string"
        ? detail
        : detail?.message || `HTTP ${response.status}`;
      throw new Error(message);
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Permintaan dibatalkan atau melewati batas waktu.");
    }
    if (error instanceof TypeError) {
      throw new Error("Backend tidak dapat dihubungi. Periksa koneksi dan server.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", abortExternal);
  }
}

export async function runSimulation({
  addresses,
  trafficCondition,
  optimization,
  demoMode,
  simulationSeed,
  signal,
}) {
  return fetchJson("/api/run-simulation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      addresses,
      traffic_condition: trafficCondition,
      optimization,
      demo_mode: demoMode,
      simulation_seed: Number(simulationSeed),
    }),
    signal,
    timeoutMs: 30000,
  });
}

export async function geoSuggest(query, { signal } = {}) {
  return fetchJson(`/api/geosuggest?q=${encodeURIComponent(query)}&limit=6`, {
    signal,
    timeoutMs: 10000,
  });
}

export async function healthCheck() {
  return fetchJson("/api/health", { timeoutMs: 5000 });
}

export { API_BASE, endpoint };
