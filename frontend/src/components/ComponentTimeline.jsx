import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api/client.js";
import { Money } from "../api/money.js";

// The component timeline: days as columns, components as stones in slots.
// Clicking a swappable stone opens the swap drawer with ranked alternatives
// and the per-signal reasoning from the intelligence engine.

const SLOT_ORDER = { morning: 0, afternoon: 1, evening: 2, overnight: 3 };

export default function ComponentTimeline({ sessionId, components, swaps, state, onMutate }) {
  const [drawer, setDrawer] = useState(null); // { component, alternatives }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const byDay = components.reduce((acc, c) => {
    (acc[c.day_index] ||= []).push(c);
    return acc;
  }, {});
  const days = Object.keys(byDay).map(Number).sort((a, b) => a - b);

  const openSwap = async (component) => {
    if (!component.is_swappable) return;
    setDrawer({ component, alternatives: [], loading: true });
    setError(null);
    try {
      const res = await api.swapAdvice(sessionId, component.component_id);
      setDrawer({ component, alternatives: res.alternatives || [], loading: false });
    } catch (e) {
      setError(e.message);
      setDrawer({ component, alternatives: [], loading: false });
    }
  };

  const doSwap = async (toComponent) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.swap(sessionId, drawer.component.component_id, toComponent.component_id);
      if (!res.applied) {
        setError(res.decision?.message || "swap blocked by budget cap");
      }
      setDrawer(null);
      onMutate?.(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          gap: 16,
          overflowX: "auto",
          paddingBottom: 8,
        }}
      >
        {days.map((day) => (
          <motion.div
            key={day}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: day * 0.06, type: "spring", stiffness: 170, damping: 22 }}
            style={{ flex: "1 1 220px", minWidth: 220 }}
          >
            <div
              className="mono"
              style={{
                fontSize: 10,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--ink-3)",
                marginBottom: 10,
              }}
            >
              Day {day}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {byDay[day]
                .sort((a, b) => SLOT_ORDER[a.slot] - SLOT_ORDER[b.slot])
                .map((comp) => {
                  const swappedOut = swaps && Object.values(swaps).includes(comp.component_id);
                  const swappedIn = swaps && Object.keys(swaps).includes(comp.component_id);
                  return (
                    <motion.button
                      key={comp.component_id}
                      layout
                      whileHover={comp.is_swappable ? { scale: 1.02, y: -2 } : {}}
                      onClick={() => openSwap(comp)}
                      disabled={!comp.is_swappable}
                      style={{
                        textAlign: "left",
                        padding: "12px 14px",
                        borderRadius: "var(--r-md)",
                        background: swappedIn
                          ? "rgba(94,234,212,0.07)"
                          : "var(--surface)",
                        border: `1px solid ${swappedIn ? "rgba(94,234,212,0.3)" : "var(--hairline)"}`,
                        opacity: swappedOut ? 0.4 : 1,
                        cursor: comp.is_swappable ? "pointer" : "default",
                        position: "relative",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <span
                          className="mono"
                          style={{ fontSize: 9, color: "var(--ink-3)", textTransform: "uppercase" }}
                        >
                          {comp.slot}
                          {comp.is_optional ? " · optional" : ""}
                        </span>
                        {comp.is_swappable && (
                          <span
                            className="mono"
                            style={{ fontSize: 9, color: "var(--aurora-1)" }}
                          >
                            swap
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, marginTop: 3 }}>
                        {comp.title}
                      </div>
                      <div className="money" style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 2 }}>
                        {fmtDelta(comp.price_delta)}
                      </div>
                    </motion.button>
                  );
                })}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Swap drawer */}
      <AnimatePresence>
        {drawer && (
          <SwapDrawer
            drawer={drawer}
            loading={loading}
            error={error}
            onPick={doSwap}
            onClose={() => setDrawer(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function fmtDelta(pair) {
  if (!pair) return "";
  const d = new Money(pair.amount, pair.currency);
  const sign = d.isNegative() ? "" : "+";
  return `${sign}${d.format()}`;
}

function SwapDrawer({ drawer, loading, error, onPick, onClose }) {
  const { component, alternatives } = drawer;
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4,6,12,0.72)",
        backdropFilter: "blur(6px)",
        zIndex: 100,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
      }}
    >
      <motion.div
        initial={{ y: "100%", opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: "100%", opacity: 0 }}
        transition={{ type: "spring", stiffness: 170, damping: 26, mass: 0.9 }}
        onClick={(e) => e.stopPropagation()}
        className="panel"
        style={{
          width: "100%",
          maxWidth: 560,
          maxHeight: "82vh",
          overflowY: "auto",
          padding: 22,
          borderRadius: "var(--r-xl) var(--r-xl) 0 0",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div
              className="mono"
              style={{ fontSize: 10, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.1em" }}
            >
              Swap alternatives
            </div>
            <div style={{ fontSize: 17, fontWeight: 600, marginTop: 2 }}>
              {component.title}
            </div>
            <div className="money" style={{ fontSize: 12, color: "var(--ink-2)" }}>
              current {fmtDelta(component.price_delta)}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "var(--ink-3)", fontSize: 18 }}
            aria-label="close"
          >
            ✕
          </button>
        </div>

        {drawer.loading && <div className="dim" style={{ marginTop: 18 }}>Finding alternatives…</div>}

        {error && (
          <div
            className="panel"
            style={{
              marginTop: 16,
              padding: 14,
              borderColor: "rgba(226,102,92,0.4)",
              color: "var(--stop)",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {!drawer.loading && alternatives.length === 0 && (
          <div className="dim" style={{ marginTop: 18 }}>
            No alternatives in this swap group — this slot is fixed.
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
          {alternatives.map((alt, i) => {
            const comp = alt.component;
            const delta = new Money(comp.price_delta.amount, comp.price_delta.currency)
              .sub(new Money(component.price_delta.amount, component.price_delta.currency));
            return (
              <motion.div
                key={comp.component_id}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05, type: "spring", stiffness: 200, damping: 24 }}
                className="panel"
                style={{ padding: 14 }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{comp.title}</div>
                    <div
                      className="money"
                      style={{
                        fontSize: 12,
                        marginTop: 2,
                        color: delta.isNegative() ? "var(--go)" : "var(--aurora-3)",
                      }}
                    >
                      {delta.isNegative() ? "−" : "+"}
                      {delta.abs().format()} net
                    </div>
                    {alt.score?.reasons?.slice(0, 2).map((r, idx) => (
                      <div
                        key={idx}
                        style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 4 }}
                      >
                        · {r.label}: {r.detail}
                      </div>
                    ))}
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ padding: "8px 16px", fontSize: 13, alignSelf: "center" }}
                    disabled={loading}
                    onClick={() => onPick(comp)}
                  >
                    Select
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}
