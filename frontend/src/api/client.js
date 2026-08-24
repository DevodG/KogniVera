const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  startSession: (payload) =>
    request("/session", { method: "POST", body: JSON.stringify(payload) }),
  getSession: (id) => request(`/session/${id}`),
  selectFlight: (id, choiceIndex) =>
    request(`/session/${id}/select-flight`, {
      method: "POST",
      body: JSON.stringify({ choice_index: choiceIndex }),
    }),
  selectHotel: (id, choiceIndex) =>
    request(`/session/${id}/select-hotel`, {
      method: "POST",
      body: JSON.stringify({ choice_index: choiceIndex }),
    }),
  negotiate: (id, payload) =>
    request(`/session/${id}/negotiate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  confirm: (id) => request(`/session/${id}/confirm`, { method: "POST" }),
};
