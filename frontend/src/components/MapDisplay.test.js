import { decodePolyline } from "./mapUtils";

test("decodes a valid polyline into latitude longitude pairs", () => {
  expect(decodePolyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")).toEqual([
    [38.5, -120.2],
    [40.7, -120.95],
    [43.252, -126.453],
  ]);
});

test("returns an empty list for malformed polyline", () => {
  expect(decodePolyline("abc")).toEqual([]);
});
