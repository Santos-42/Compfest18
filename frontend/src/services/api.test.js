import { endpoint, runSimulation } from "./api";

test("uses relative API path by default", () => {
  expect(endpoint("/api/health")).toBe("/api/health");
});

test("sends the new snake_case simulation contract", async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ status: "success" }),
  });

  await runSimulation({
    addresses: [{ address: "Alamat A", cod_amount: 100000 }],
    trafficCondition: "normal",
    optimization: "distance",
    demoMode: true,
    simulationSeed: 42,
  });

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/run-simulation",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        addresses: [{ address: "Alamat A", cod_amount: 100000 }],
        traffic_condition: "normal",
        optimization: "distance",
        demo_mode: true,
        simulation_seed: 42,
      }),
    }),
  );
});
