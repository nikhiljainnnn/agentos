import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../lib/store";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, register } = useStore();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!username || !password) return;
    setLoading(true);
    setError("");
    try {
      if (mode === "login") await login(username, password);
      else await register(username, email, password);
      navigate("/");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Authentication failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-base flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(108,99,255,0.12) 0%, transparent 70%)" }} />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)" }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(108,99,255,0.04) 0%, transparent 60%)" }} />
      </div>

      <div className="w-full max-w-sm relative animate-fade-up">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="relative inline-flex mb-5">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{
                background: "linear-gradient(135deg, #6C63FF, #8B5CF6)",
                boxShadow: "0 0 32px rgba(108,99,255,0.4), 0 8px 24px rgba(0,0,0,0.3)"
              }}>
              <svg width="28" height="28" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
              </svg>
            </div>
            <div className="absolute -inset-1 rounded-2xl opacity-40 blur-md"
              style={{ background: "linear-gradient(135deg, #6C63FF, #8B5CF6)" }} />
          </div>
          <h1 className="text-3xl font-semibold text-t1 tracking-tight mb-1">AgentOS</h1>
          <p className="text-t3 text-sm">Production Multi-Agent RAG Platform</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-6"
          style={{
            background: "var(--surface-a)",
            border: "1px solid var(--border-md)",
            boxShadow: "0 24px 64px rgba(0,0,0,0.5)"
          }}>

          {/* Mode tabs */}
          <div className="flex p-1 mb-6 rounded-xl" style={{ background: "var(--base)" }}>
            {(["login", "register"] as const).map((m) => (
              <button key={m} onClick={() => { setMode(m); setError(""); }}
                className="flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 capitalize"
                style={mode === m
                  ? { background: "var(--accent)", color: "#fff", boxShadow: "0 2px 12px rgba(108,99,255,0.4)" }
                  : { color: "var(--text-3)" }
                }>
                {m}
              </button>
            ))}
          </div>

          {/* Fields */}
          <div className="space-y-3">
            <div className="relative">
              <input type="text" placeholder="Username" value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200"
                style={{
                  background: "var(--surface-b)",
                  border: "1px solid var(--border-md)",
                  color: "var(--text-1)",
                }}
                onFocus={e => e.target.style.borderColor = "var(--accent)"}
                onBlur={e => e.target.style.borderColor = "var(--border-md)"}
              />
            </div>

            {mode === "register" && (
              <input type="email" placeholder="Email address" value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200 animate-fade-in"
                style={{
                  background: "var(--surface-b)",
                  border: "1px solid var(--border-md)",
                  color: "var(--text-1)",
                }}
                onFocus={e => e.target.style.borderColor = "var(--accent)"}
                onBlur={e => e.target.style.borderColor = "var(--border-md)"}
              />
            )}

            <input type="password" placeholder="Password" value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSubmit()}
              className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200"
              style={{
                background: "var(--surface-b)",
                border: "1px solid var(--border-md)",
                color: "var(--text-1)",
              }}
              onFocus={e => e.target.style.borderColor = "var(--accent)"}
              onBlur={e => e.target.style.borderColor = "var(--border-md)"}
            />

            {error && (
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs animate-fade-in"
                style={{ background: "var(--rose-dim)", border: "1px solid rgba(244,63,94,0.2)", color: "var(--rose)" }}>
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {error}
              </div>
            )}

            <button onClick={handleSubmit}
              disabled={loading || !username || !password}
              className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all duration-200 mt-1 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              style={{
                background: "linear-gradient(135deg, var(--accent), var(--violet))",
                boxShadow: loading ? "none" : "0 4px 20px rgba(108,99,255,0.4)",
              }}>
              {loading ? (
                <svg className="animate-spin" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" strokeLinecap="round"/>
                </svg>
              ) : null}
              {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </div>
        </div>

        {/* Stack labels */}
        <div className="flex items-center justify-center gap-3 mt-6">
          {["FastAPI", "LangGraph", "Azure AI", "React"].map((t, i) => (
            <span key={i} className="text-xs" style={{ color: "var(--text-4)" }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
