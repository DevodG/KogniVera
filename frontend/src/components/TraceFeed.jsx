import { motion, AnimatePresence } from "framer-motion";

// The live agent trace — the transparency feature. Every reasoning step,
// tool call and decision the engine made, in order.

export default function TraceFeed({ trace, open }) {
  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 170, damping: 26 }}
          className="panel"
          style={{
            marginTop: 16,
            overflow: "hidden",
            maxHeight: 280,
            overflowY: "auto",
          }}
        >
          <div style={{ padding: 16 }}>
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
              Agent trace · {trace?.length || 0} entries
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {(trace || []).map((entry, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 26 }}
                  style={{
                    display: "flex",
                    gap: 10,
                    fontSize: 12,
                    fontFamily: "var(--font-mono)",
                    lineHeight: 1.5,
                  }}
                >
                  <span style={{ color: "var(--ink-3)", flexShrink: 0 }}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    style={{
                      flexShrink: 0,
                      width: 74,
                      color:
                        entry.kind === "decision"
                          ? "var(--aurora-3)"
                          : entry.kind === "tool_call"
                          ? "var(--aurora-1)"
                          : entry.kind === "reasoning"
                          ? "var(--aurora-2)"
                          : "var(--ink-3)",
                    }}
                  >
                    {entry.kind}
                  </span>
                  <span style={{ color: "var(--ink-2)" }}>{entry.content}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
