import { useState, useEffect } from "react";
import { api } from "../api/client.js";

export default function ComponentSwapper({ packageId, budgetCap, runningTotal, onTotalChange }) {
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // State for the swap modal/panel
  const [activeSwapComponent, setActiveSwapComponent] = useState(null);
  const [alternatives, setAlternatives] = useState([]);
  const [loadingAlts, setLoadingAlts] = useState(false);
  
  // Keep track of which components we've swapped { originalComponentId: currentComponent }
  const [swaps, setSwaps] = useState({});

  useEffect(() => {
    if (!packageId) return;
    
    async function fetchComponents() {
      setLoading(true);
      try {
        const res = await api.getComponents(packageId);
        setComponents(res.components || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchComponents();
  }, [packageId]);

  const handleOpenSwap = async (component) => {
    setActiveSwapComponent(component);
    setLoadingAlts(true);
    setAlternatives([]);
    try {
      const res = await api.getAlternatives(packageId, component.component_id);
      setAlternatives(res.alternatives || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAlts(false);
    }
  };

  const handleConfirmSwap = async (alt) => {
    if (!activeSwapComponent) return;
    
    try {
      const res = await api.swapComponent(packageId, activeSwapComponent.component_id, alt.component_id);
      
      const delta = parseFloat(res.delta_inr);
      if (runningTotal + delta > budgetCap) {
        alert("This swap exceeds your budget cap!");
        return;
      }
      
      // Update local swaps
      setSwaps({
        ...swaps,
        [activeSwapComponent.component_id]: alt
      });
      
      // Update parent running total
      onTotalChange(runningTotal + delta);
      
      setActiveSwapComponent(null);
    } catch (err) {
      alert("Swap failed: " + err.message);
    }
  };

  if (loading) return <div className="dim">Loading itinerary...</div>;
  if (error) return <div style={{ color: "var(--stop)" }}>{error}</div>;
  if (!components.length) return null;

  return (
    <div className="panel slide-up" style={{ padding: 24, marginTop: 24 }}>
      <div className="section-header" style={{ fontSize: 20, marginBottom: 16 }}>
        Customize Your Itinerary
      </div>
      <div className="dim" style={{ fontSize: 13, marginBottom: 20 }}>
        Swap out activities or hotels to build your perfect trip. Prices will adjust automatically.
      </div>
      
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {components.map((comp) => {
          const current = swaps[comp.component_id] || comp;
          
          return (
            <div key={comp.component_id} style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center",
              padding: 16,
              border: "1px solid var(--line)",
              borderRadius: 8,
              background: swaps[comp.component_id] ? "var(--panel-sunken)" : "transparent"
            }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--dim)", textTransform: "uppercase", marginBottom: 4 }}>
                  Day {current.day_index} • {current.slot}
                </div>
                <div style={{ fontWeight: 600 }}>{current.title}</div>
              </div>
              
              {comp.is_swappable === 1 && (
                <button 
                  className="btn-secondary" 
                  style={{ padding: "6px 12px", fontSize: 12 }}
                  onClick={() => handleOpenSwap(current)}
                >
                  Swap
                </button>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Swap Alternatives Modal/Panel */}
      {activeSwapComponent && (
        <div style={{ 
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0, 
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 100
        }}>
          <div className="panel" style={{ padding: 24, width: "100%", maxWidth: 500, maxHeight: "80vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <div className="section-header" style={{ fontSize: 18 }}>Swap alternatives</div>
              <button onClick={() => setActiveSwapComponent(null)} style={{ background: "none", border: "none", color: "var(--dim)", cursor: "pointer" }}>✕</button>
            </div>
            
            <div style={{ marginBottom: 16, padding: 12, background: "var(--panel-sunken)", borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: "var(--dim)" }}>Currently selected:</div>
              <div style={{ fontWeight: 600 }}>{activeSwapComponent.title}</div>
            </div>
            
            {loadingAlts ? (
              <div className="dim">Finding alternatives...</div>
            ) : alternatives.length === 0 ? (
              <div className="dim">No alternatives available for this slot.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {alternatives.map(alt => {
                  const delta = parseFloat(alt.price_delta) - parseFloat(activeSwapComponent.price_delta);
                  const isOverBudget = runningTotal + delta > budgetCap;
                  
                  return (
                    <div key={alt.component_id} style={{ 
                      padding: 16, 
                      border: "1px solid var(--line)", 
                      borderRadius: 8,
                      opacity: isOverBudget ? 0.5 : 1
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                        <div style={{ fontWeight: 600 }}>{alt.title}</div>
                        <div style={{ 
                          color: delta > 0 ? "var(--stop)" : delta < 0 ? "var(--signal)" : "var(--dim)",
                          fontWeight: 600
                        }}>
                          {delta > 0 ? "+" : ""}{delta} {alt.currency}
                        </div>
                      </div>
                      
                      <button 
                        className="btn-primary" 
                        style={{ width: "100%", padding: 8 }}
                        disabled={isOverBudget}
                        onClick={() => handleConfirmSwap(alt)}
                      >
                        {isOverBudget ? "Over Budget" : "Select"}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
