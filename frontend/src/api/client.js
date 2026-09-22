// API client — thin fetch wrapper. Money arrives as {amount: string, currency}
// and is never touched as a number here.

const BASE = "/api";

async function req(path, { method = "GET", body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`bad JSON from ${path}`);
  }
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

export const api = {
  health: () => req("/health"),

  // session
  createSession: (profile) => req("/session", { method: "POST", body: profile }),
  getSession: (id) => req(`/session/${id}`),

  // packages
  listPackages: (params = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v != null && v !== "")
    ).toString();
    return req(`/packages${q ? `?${q}` : ""}`);
  },
  recommend: (sessionId, limit = 8) =>
    req(`/packages/recommend/${sessionId}?limit=${limit}`),
  packageDetail: (id) => req(`/packages/${id}`),
  choosePackage: (sessionId, packageId) =>
    req(`/session/${sessionId}/choose/${packageId}`, { method: "POST" }),

  // swapping
  swapAdvice: (sessionId, componentId) =>
    req(`/session/${sessionId}/swap-advice/${componentId}`),
  swap: (sessionId, fromId, toId) =>
    req(`/session/${sessionId}/swap`, {
      method: "POST",
      body: { from_component_id: fromId, to_component_id: toId },
    }),
  unswap: (sessionId, componentId) =>
    req(`/session/${sessionId}/unswap/${componentId}`, { method: "POST" }),

  // optional add-ons
  addOptional: (sessionId, componentId) =>
    req(`/session/${sessionId}/optional/${componentId}`, { method: "POST" }),
  removeOptional: (sessionId, componentId) =>
    req(`/session/${sessionId}/optional/${componentId}`, { method: "DELETE" }),

  // guides
  recommendGuides: (sessionId, onDate) =>
    req(`/guides/recommend/${sessionId}${onDate ? `?on_date=${onDate}` : ""}`),
  attachGuide: (sessionId, guideId, onDate) =>
    req(`/session/${sessionId}/guide/${guideId}${onDate ? `?on_date=${onDate}` : ""}`, {
      method: "POST",
    }),

  // explainability
  explain: (entityId) => req(`/explain/${entityId}`),
};
