import { buildRouteMarkers } from "./mapUtils";

test("maps marker position and ETA using route order", () => {
  const markers = buildRouteMarkers(
    [0, 2, 1, 3, 0],
    [[0, 0], [10, 10], [20, 20], [30, 30]],
    [
      { stop: 1, order_index: 2, eta: "09:10" },
      { stop: 2, order_index: 1, eta: "09:20" },
      { stop: 3, order_index: 3, eta: "09:30" },
    ],
    [{ address: "A" }, { address: "B" }, { address: "C" }],
  );

  expect(markers).toHaveLength(4);
  expect(markers[0].isOrigin).toBe(true);
  expect(markers[1]).toMatchObject({ nodeIndex: 2, position: [20, 20], address: "B", label: 1 });
  expect(markers[2]).toMatchObject({ nodeIndex: 1, position: [10, 10], address: "A", label: 2 });
  expect(markers[3]).toMatchObject({ nodeIndex: 3, position: [30, 30], address: "C", label: 3 });
});
