/**
 * api.js — HTTP client untuk backend FastAPI.
 * Base URL dapat dikonfigurasi via REACT_APP_API_URL.
 */
const API_BASE =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

export async function runSimulation({ addresses, codAmounts, trafficCondition }) {
  const res = await fetch(`${API_BASE}/api/run-simulation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      addresses,
      cod_amounts: codAmounts,
      traffic_condition: trafficCondition,
    }),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}
