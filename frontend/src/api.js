/**
 * API client. All money values are strings on the wire.
 * The browser never computes a total; it only displays server figures.
 */
const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const detail = body.detail || `request failed (${res.status})`;
    const error = new Error(detail);
    error.status = res.status;
    error.body = body;
    throw error;
  }
  return body;
}

export function getHealth() {
  return request("/health");
}

export function getCities() {
  return request("/cities");
}

export function getLanguages() {
  return request("/languages");
}

export function getCityPackages(cityId) {
  return request(`/city-packages/${encodeURIComponent(cityId)}`);
}

export function recommend(payload) {
  return request("/planner/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function selectPackage(sessionId, packageId) {
  return request(
    `/sessions/${sessionId}/select-package?package_id=${encodeURIComponent(packageId)}`,
    { method: "POST" },
  );
}

export function getSession(sessionId) {
  return request(`/sessions/${sessionId}`);
}

export function getItinerary(sessionId) {
  return request(`/sessions/${sessionId}/itinerary`);
}

export function swapComponent(sessionId, componentId, replacementId) {
  return request(`/sessions/${sessionId}/swap-component`, {
    method: "POST",
    body: JSON.stringify({
      component_id: componentId,
      replacement_component_id: replacementId,
    }),
  });
}

export function selectGuide(sessionId, guideId, service) {
  return request(`/sessions/${sessionId}/select-guide`, {
    method: "POST",
    body: JSON.stringify({ guide_id: guideId, service }),
  });
}

export function getGuides(sessionId) {
  return request(`/sessions/${sessionId}/guides`);
}

export function negotiate(sessionId, option, extra = {}) {
  return request(`/sessions/${sessionId}/negotiate`, {
    method: "POST",
    body: JSON.stringify({ option, ...extra }),
  });
}

export function getTrustReceipt(sessionId) {
  return request(`/sessions/${sessionId}/trust-receipt`);
}

export function confirm(sessionId) {
  return request(`/sessions/${sessionId}/confirm`, { method: "POST", body: "{}" });
}

export function getFlights(sessionId) {
  return request(`/sessions/${sessionId}/flights`);
}

export function selectFlight(sessionId, flight) {
  return request(`/sessions/${sessionId}/select-flight`, {
    method: "POST",
    body: JSON.stringify(flight),
  });
}

export function getHotels(sessionId) {
  return request(`/sessions/${sessionId}/hotels`);
}

export function selectHotel(sessionId, hotel) {
  return request(`/sessions/${sessionId}/select-hotel`, {
    method: "POST",
    body: JSON.stringify(hotel),
  });
}
