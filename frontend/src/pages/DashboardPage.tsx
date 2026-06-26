import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../lib/store";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

const PROVIDER_COLOR: Record<string, string> = {
  azure: "#60A5FA", anthropic: "#FB923C", google: "#34D399",
};
const PROVIDER_BG: Record<string, string> = {
  azure: "rgba(96,165,250,0.1)", anthropic: "rgba(251,146,60,0.1)", google: "rgba(52,211,153,0.1)",
};

const ChartTooltipStyle = {
  contentStyle: { background: "#111D35", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 10, fontSize: 12, color: "#94A3C4" },
  cursor: { stroke: "rgba(108,99,255,0.2)", strokeWidth: 1 },
};

/* Mock sparkline data */
const latencyHistory = Array.from({ length: 24 }, (_, i) => ({
  t: `${i}:00`, ms: 600 + Math.random() * 600,
}));
const evalHistory = Array.from({ length: 24 }, (_, i) => ({
  t: `${i}:00`, score: 0.78 + Math.random() * 0.18,
}));

function StatCard({ label, value, sub, color, Icon }: {
  label: string; value: string | number; sub?: string; color: string; Icon: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl p-5 transition-all duration-200 hover:scale-[1.01]"
      style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: color + "22", color }}>{Icon}</div>
        {sub && <span className="text-[10px] px-2 py-0.5 rounded-full font-mono"
          style={{ background: "rgba(16,185,129,0.1)", color: "#10B981" }}>{sub}</span>}
      </div>
      <div className="text-2xl font-semibold mb-0.5" style={{ color: "var(--text-1)" }}>{value}</div>
      <div className="text-xs" style={{ color: "var(--text-3)" }}>{label}</div>
    </div>
  );
}

const icons = {
  trend: <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  clock: <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  check: <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  alert: <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  retry: <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>,
  back:  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>,
};

export function DashboardPage() {
  const navigate = useNavigate();
  const { metrics, providerStats, fetchMetrics, fetchProviderStats } = useStore();
  const [activeTab, setActiveTab] = useState<"overview" | "providers" | "eval">("overview");

  useEffect(() => {
    fetchMetrics(); fetchProviderStats();
    const id = setInterval(() => { fetchMetrics(); fetchProviderStats(); }, 10_000);
    return () => clearInterval(id);
  }, []);

  const pieData = metrics
    ? Object.entries(metrics.provider_distribution).map(([name, value]) => ({ name, value }))
    : [{ name: "azure", value: 1 }];

  const barData = Object.entries(providerStats).map(([name, s]: [string, any]) => ({
    name, latency: Math.round(s.avg_latency_ms ?? 0), calls: s.calls ?? 0, errors: s.errors ?? 0,
  }));

  return (
    <div className="min-h-screen" style={{ background: "var(--base)", color: "var(--text-1)" }}>

      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center gap-4 px-6 h-14"
        style={{ background: "rgba(7,11,20,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--border)" }}>
        <button onClick={() => navigate("/")}
          className="flex items-center gap-2 text-xs transition-colors duration-150 hover:text-t1"
          style={{ color: "var(--text-3)" }}>
          {icons.back} Back to chat
        </button>
        <div className="w-px h-4 mx-1" style={{ background: "var(--border-md)" }} />
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--violet))" }}>
            <svg width="12" height="12" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
          </div>
          <span className="text-sm font-semibold">AgentOS Dashboard</span>
        </div>
        <div className="ml-auto">
          <span className="text-[10px] px-2 py-1 rounded-full font-mono"
            style={{ background: "rgba(16,185,129,0.1)", color: "#10B981", border: "1px solid rgba(16,185,129,0.2)" }}>
            ● Live
          </span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Queries today" value={metrics?.total_queries_today ?? "—"}
            sub="+12%" color="#6C63FF" Icon={icons.trend} />
          <StatCard label="Avg latency" value={metrics ? `${metrics.avg_latency_ms.toFixed(0)}ms` : "—"}
            color="#60A5FA" Icon={icons.clock} />
          <StatCard label="Eval pass rate" value={metrics ? `${(metrics.eval_pass_rate * 100).toFixed(1)}%` : "—"}
            color="#10B981" Icon={icons.check} />
          <StatCard label="Error rate" value={metrics ? `${(metrics.error_rate * 100).toFixed(2)}%` : "—"}
            color="#F43F5E" Icon={icons.alert} />
        </div>

        {/* Tab nav */}
        <div className="flex gap-1 p-1 rounded-xl w-fit"
          style={{ background: "var(--surface-a)", border: "1px solid var(--border)" }}>
          {(["overview", "providers", "eval"] as const).map(t => (
            <button key={t} onClick={() => setActiveTab(t)}
              className="px-4 py-1.5 rounded-lg text-xs font-medium capitalize transition-all duration-150"
              style={activeTab === t
                ? { background: "var(--accent)", color: "#fff", boxShadow: "0 2px 10px rgba(108,99,255,0.4)" }
                : { color: "var(--text-3)" }
              }>{t}</button>
          ))}
        </div>

        {/* ── Overview tab ── */}
        {activeTab === "overview" && (
          <div className="space-y-6 animate-fade-in">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* Latency area chart */}
              <div className="rounded-2xl p-5" style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
                <p className="text-xs font-medium mb-4" style={{ color: "var(--text-2)" }}>Latency over 24h (ms)</p>
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={latencyHistory}>
                    <defs>
                      <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6C63FF" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#6C63FF" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="t" tick={{ fill: "#4E6080", fontSize: 10 }} tickLine={false} axisLine={false} interval={5} />
                    <YAxis tick={{ fill: "#4E6080", fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip {...ChartTooltipStyle} formatter={(v: any) => [`${Math.round(v)}ms`, "Latency"]} />
                    <Area type="monotone" dataKey="ms" stroke="#6C63FF" strokeWidth={2} fill="url(#latGrad)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Eval score area chart */}
              <div className="rounded-2xl p-5" style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
                <p className="text-xs font-medium mb-4" style={{ color: "var(--text-2)" }}>Eval score over 24h</p>
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={evalHistory}>
                    <defs>
                      <linearGradient id="evalGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="t" tick={{ fill: "#4E6080", fontSize: 10 }} tickLine={false} axisLine={false} interval={5} />
                    <YAxis tick={{ fill: "#4E6080", fontSize: 10 }} tickLine={false} axisLine={false} domain={[0.5, 1]} />
                    <Tooltip {...ChartTooltipStyle} formatter={(v: any) => [`${(v * 100).toFixed(0)}%`, "Score"]} />
                    <Area type="monotone" dataKey="score" stroke="#10B981" strokeWidth={2} fill="url(#evalGrad)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Provider donut + bar */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-2xl p-5" style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
                <p className="text-xs font-medium mb-4" style={{ color: "var(--text-2)" }}>Provider distribution</p>
                <div className="flex items-center gap-6">
                  <ResponsiveContainer width={130} height={130}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={38} outerRadius={58}
                        dataKey="value" strokeWidth={0}>
                        {pieData.map(e => <Cell key={e.name} fill={PROVIDER_COLOR[e.name] ?? "#6C63FF"} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2.5 flex-1">
                    {pieData.map(e => {
                      const total = pieData.reduce((a, x) => a + x.value, 0);
                      const pct = total ? Math.round(e.value / total * 100) : 0;
                      const color = PROVIDER_COLOR[e.name] ?? "#6C63FF";
                      return (
                        <div key={e.name} className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                          <span className="text-xs capitalize flex-1" style={{ color: "var(--text-2)" }}>{e.name}</span>
                          <span className="text-xs font-mono" style={{ color }}>{pct}%</span>
                        </div>
                      );
                    })}
                    {pieData.length === 0 && (
                      <p className="text-xs" style={{ color: "var(--text-4)" }}>No data yet</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl p-5" style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
                <p className="text-xs font-medium mb-4" style={{ color: "var(--text-2)" }}>Avg latency by provider (ms)</p>
                {barData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={130}>
                    <BarChart data={barData} barSize={28}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: "#4E6080", fontSize: 11 }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fill: "#4E6080", fontSize: 10 }} tickLine={false} axisLine={false} />
                      <Tooltip {...ChartTooltipStyle} formatter={(v: any) => [`${Math.round(v)}ms`, "Latency"]} />
                      <Bar dataKey="latency" radius={[6, 6, 0, 0]}>
                        {barData.map(e => <Cell key={e.name} fill={PROVIDER_COLOR[e.name] ?? "#6C63FF"} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-32 flex items-center justify-center text-xs" style={{ color: "var(--text-4)" }}>
                    No LLM calls made yet
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Providers tab ── */}
        {activeTab === "providers" && (
          <div className="animate-fade-in rounded-2xl overflow-hidden"
            style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Provider", "Calls", "Errors", "Avg Latency", "Error Rate", "Status"].map(h => (
                    <th key={h} className="text-left px-5 py-3.5 text-xs font-medium" style={{ color: "var(--text-3)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(Object.entries(providerStats).length > 0
                  ? Object.entries(providerStats)
                  : [["azure", { calls: 0, errors: 0, avg_latency_ms: 0, error_rate: 0 }],
                     ["anthropic", { calls: 0, errors: 0, avg_latency_ms: 0, error_rate: 0 }],
                     ["google", { calls: 0, errors: 0, avg_latency_ms: 0, error_rate: 0 }]]
                ).map(([name, s]: [string, any]) => {
                  const color = PROVIDER_COLOR[name] ?? "#6C63FF";
                  const ok = (s.error_rate ?? 0) < 0.05;
                  return (
                    <tr key={name} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium"
                          style={{ background: PROVIDER_BG[name] ?? "var(--accent-dim)", color }}>
                          <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                          {name}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs" style={{ color: "var(--text-2)" }}>{s.calls ?? 0}</td>
                      <td className="px-5 py-3.5 font-mono text-xs" style={{ color: (s.errors ?? 0) > 0 ? "#F43F5E" : "var(--text-3)" }}>{s.errors ?? 0}</td>
                      <td className="px-5 py-3.5 font-mono text-xs" style={{ color: "var(--text-2)" }}>{Math.round(s.avg_latency_ms ?? 0)}ms</td>
                      <td className="px-5 py-3.5 font-mono text-xs" style={{ color: ok ? "#10B981" : "#F43F5E" }}>
                        {((s.error_rate ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full"
                          style={ok
                            ? { background: "rgba(16,185,129,0.1)", color: "#10B981", border: "1px solid rgba(16,185,129,0.2)" }
                            : { background: "rgba(244,63,94,0.1)", color: "#F43F5E", border: "1px solid rgba(244,63,94,0.2)" }}>
                          <div className="w-1 h-1 rounded-full" style={{ background: ok ? "#10B981" : "#F43F5E" }} />
                          {ok ? "Healthy" : "Degraded"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Eval tab ── */}
        {activeTab === "eval" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
            {[
              { label: "Faithfulness", color: "#6C63FF", desc: "Grounded in retrieved context" },
              { label: "Relevancy", color: "#10B981", desc: "Directly addresses the query" },
              { label: "Precision", color: "#8B5CF6", desc: "No irrelevant context included" },
            ].map(({ label, color, desc }) => {
              const score = 0.78 + Math.random() * 0.18;
              const pct = Math.round(score * 100);
              return (
                <div key={label} className="rounded-2xl p-5"
                  style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm font-medium" style={{ color: "var(--text-1)" }}>{label}</p>
                    <span className="text-lg font-semibold font-mono" style={{ color }}>{pct}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full overflow-hidden mb-3" style={{ background: "var(--surface-c)" }}>
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-3)" }}>{desc}</p>
                  <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                    <p className="text-[10px] font-mono mb-2" style={{ color: "var(--text-4)" }}>Last 24h distribution</p>
                    <div className="flex items-end gap-0.5 h-8">
                      {Array.from({ length: 24 }, (_, i) => {
                        const h = 0.4 + Math.random() * 0.6;
                        return <div key={i} className="flex-1 rounded-sm" style={{ height: `${h * 100}%`, background: color, opacity: 0.3 + h * 0.7 }} />;
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
            {/* Pass rate gauge */}
            <div className="lg:col-span-3 rounded-2xl p-5 flex items-center gap-8"
              style={{ background: "var(--surface-b)", border: "1px solid var(--border)" }}>
              <div>
                <p className="text-xs mb-1" style={{ color: "var(--text-3)" }}>Overall pass rate</p>
                <p className="text-4xl font-semibold font-mono" style={{ color: "#10B981" }}>
                  {metrics ? `${(metrics.eval_pass_rate * 100).toFixed(1)}%` : "91.5%"}
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--text-4)" }}>threshold: 65.0</p>
              </div>
              <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ background: "var(--surface-c)" }}>
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: metrics ? `${metrics.eval_pass_rate * 100}%` : "91.5%",
                    background: "linear-gradient(90deg, #6C63FF, #10B981)" }} />
              </div>
              <div>
                <p className="text-xs mb-1" style={{ color: "var(--text-3)" }}>Retries triggered</p>
                <p className="text-2xl font-semibold font-mono" style={{ color: "#F59E0B" }}>8</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-4)" }}>last 24h</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
