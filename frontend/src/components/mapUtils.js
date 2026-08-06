export function buildRouteMarkers(routeOrder, coordinates, etaList = [], addresses = [], locations = []) {
  return routeOrder
    .map((nodeIndex, routePosition) => {
      const coordinate = coordinates[nodeIndex];
      if (!coordinate) return null;
      const [lng, lat] = coordinate;
      const isOrigin = nodeIndex === 0;
      const eta = etaList.find((item) => item.order_index === nodeIndex) || null;
      const address = addresses?.[nodeIndex - 1]?.address || locations?.[nodeIndex - 1]?.address || "";
      return {
        nodeIndex,
        routePosition,
        position: [lat, lng],
        isOrigin,
        label: eta?.stop || routePosition,
        eta,
        address,
        location: locations?.[nodeIndex - 1],
      };
    })
    .filter(Boolean)
    .filter((marker, index) => !marker.isOrigin || index === 0);
}

export function decodePolyline(value) {
  if (!value) return [];
  const result = [];
  let index = 0;
  let latitude = 0;
  let longitude = 0;
  try {
    while (index < value.length) {
      const latitudeDelta = decodeValue(value, index);
      index = latitudeDelta.index;
      const longitudeDelta = decodeValue(value, index);
      index = longitudeDelta.index;
      latitude += latitudeDelta.value;
      longitude += longitudeDelta.value;
      result.push([latitude / 100000, longitude / 100000]);
    }
  } catch (_) {
    return [];
  }
  return result;
}

function decodeValue(value, start) {
  let result = 0;
  let shift = 0;
  let index = start;
  let byte;
  do {
    if (index >= value.length) throw new Error("Malformed polyline");
    byte = value.charCodeAt(index++) - 63;
    if (byte < 0) throw new Error("Malformed polyline");
    result |= (byte & 0x1f) << shift;
    shift += 5;
  } while (byte >= 0x20);
  return {
    value: result & 1 ? ~(result >> 1) : result >> 1,
    index,
  };
}
