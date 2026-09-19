import { useState } from "react";

export default function AuthModal({ onClose, onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authentication failed");

      localStorage.setItem("token", data.access_token);
      onLoginSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000
    }}>
      <div className="panel" style={{ padding: 32, width: "100%", maxWidth: 400, position: "relative" }}>
        <button onClick={onClose} style={{ position: "absolute", top: 16, right: 16, background: "none", border: "none", color: "var(--dim)", cursor: "pointer" }}>✕</button>
        
        <div className="section-header" style={{ fontSize: 24, marginBottom: 24, textAlign: "center" }}>
          {isLogin ? "Welcome Back" : "Create Account"}
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "var(--dim)", marginBottom: 6 }}>Email</label>
            <input 
              type="email" 
              required
              className="input-field" 
              style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid var(--line)", background: "var(--panel-raised)", color: "var(--ink)" }}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "var(--dim)", marginBottom: 6 }}>Password</label>
            <input 
              type="password" 
              required
              className="input-field" 
              style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid var(--line)", background: "var(--panel-raised)", color: "var(--ink)" }}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          
          {error && <div style={{ color: "var(--stop)", fontSize: 13 }}>{error}</div>}

          <button 
            type="submit" 
            className="btn-primary" 
            disabled={loading}
            style={{ padding: "12px", marginTop: 8 }}
          >
            {loading ? "Processing..." : (isLogin ? "Sign In" : "Register")}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: "center", fontSize: 13, color: "var(--dim)" }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button 
            onClick={() => setIsLogin(!isLogin)} 
            style={{ background: "none", border: "none", color: "var(--signal)", cursor: "pointer", fontWeight: 600 }}
          >
            {isLogin ? "Sign up" : "Log in"}
          </button>
        </div>
      </div>
    </div>
  );
}
