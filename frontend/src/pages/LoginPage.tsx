import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../lib/store";
import { Zap, Loader2 } from "lucide-react";

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
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, email, password);
      }
      navigate("/");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center font-sans">
      <div className="w-full max-w-sm px-6">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Zap size={28} />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">AgentOS</h1>
          <p className="text-slate-400 text-sm mt-1">Production Multi-Agent RAG Platform</p>
        </div>

        {/* Tab toggle */}
        <div className="flex bg-slate-800 rounded-xl p-1 mb-6">
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all capitalize ${
                mode === m ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="space-y-3">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          {mode === "register" && (
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          )}
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />

          {error && (
            <p className="text-red-400 text-xs px-1">{error}</p>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading || !username || !password}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : null}
            {mode === "login" ? "Sign in" : "Create account"}
          </button>
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          Built with FastAPI · LangGraph · Azure AI · React
        </p>
      </div>
    </div>
  );
}
