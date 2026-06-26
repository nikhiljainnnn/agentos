import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../lib/store";
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip,
  ResponsiveContainer, LineChart, Line, CartesianGrid
} from "recharts";
import { ArrowLeft, Zap, Clock, CheckCircle, AlertCircle, TrendingUp } from "lucide-react";

const PROVIDER_COLORS = {
  azure: "#3b82f6",
  anthropic: "#f97316",
  google: "#22c55e",
};

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: string | number; icon: any; color: string;
}) {
  return (
    <div className="bg-slate-800 rounded-2xl p-5 border border-slate-700">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${color}`}>
        <Icon size={20} />
      </div>
      <div className="text-2xl font-bold text-white mb-0.5">{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
    </div>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { metrics, providerStats, fetchMetrics, fetchProviderStats } = useStore();

  useEffect(() => {
    fetchMetrics();
    fetchProviderStats();
    const interval = setInterval(() => { fetchMetrics(); fetchProviderStats(); }, 10000);
    return () => clearInterval(interval);
  }, []);

  const providerPieData = metrics
    ? Object.entries(metrics.provider_distribution).map(([name, value]) => ({ name, value }))
    : [];

  const providerBarData = Object.entries(providerStats).map(([name, stats]: [string, any]) => ({
    name,
    avg_latency: stats.avg_latency_ms || 0,
    calls: stats.calls || 0,
    errors: stats.errors || 0,
  }));

  const evalData = [
    { name: "Faithfulness", score: 0 },
    { name: "Relevancy", score: 0 },
    { name: "Precision", score: 0 },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      <header className="border-b border-slate-800 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={16} /> Back to Chat
        </button>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-indigo-600 rounded-lg flex items-center justify-center">
            <Zap size={12} />
          </div>
          <span className="font-bold">AgentOS Dashboard</span>
        </div>
      </header>

      <div className="p-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Queries Today"
            value={metrics?.total_queries_today ?? "—"}
            icon={TrendingUp}
            color="bg-indigo-600/20 text-indigo-400"
          />
          <StatCard
            label="Avg Latency"
            value={metrics ? `${metrics.avg_latency_ms.toFixed(0)}ms` : "—"}
            icon={Clock}
            color="bg-blue-600/20 text-blue-400"
          />
          <StatCard
            label="Eval Pass Rate"
            value={metrics ? `${(metrics.eval_pass_rate * 100).toFixed(1)}%` : "—"}
            icon={CheckCircle}
            color="bg-emerald-600/20 text-emerald-400"
          />
          <StatCard
            label="Error Rate"
            value={metrics ? `${(metrics.error_rate * 100).toFixed(2)}%` : "—"}
            icon={AlertCircle}
            color="bg-red-600/20 text-red-400"
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Provider distribution pie */}
          <div className="bg-slate-800 rounded-2xl p-5 border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Provider Distribution</h3>
            {providerPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={providerPieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {providerPieData.map((entry) => (
                      <Cell key={entry.name} fill={(PROVIDER_COLORS as any)[entry.name] || "#6b7280"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
                No data yet — send some messages first
              </div>
            )}
          </div>

          {/* Provider latency bar chart */}
          <div className="bg-slate-800 rounded-2xl p-5 border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Provider Avg Latency (ms)</h3>
            {providerBarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={providerBarData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                  <Bar dataKey="avg_latency" radius={[4, 4, 0, 0]}>
                    {providerBarData.map((entry) => (
                      <Cell key={entry.name} fill={(PROVIDER_COLORS as any)[entry.name] || "#6366f1"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
                No provider data yet
              </div>
            )}
          </div>
        </div>

        {/* Provider stats table */}
        <div className="bg-slate-800 rounded-2xl p-5 border border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Provider Health</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 text-left border-b border-slate-700">
                <th className="pb-3 font-medium">Provider</th>
                <th className="pb-3 font-medium">Calls</th>
                <th className="pb-3 font-medium">Errors</th>
                <th className="pb-3 font-medium">Avg Latency</th>
                <th className="pb-3 font-medium">Error Rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(providerStats).map(([name, stats]: [string, any]) => (
                <tr key={name} className="border-b border-slate-700/50">
                  <td className="py-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold`}
                      style={{ background: `${(PROVIDER_COLORS as any)[name]}20`, color: (PROVIDER_COLORS as any)[name] }}
                    >
                      {name}
                    </span>
                  </td>
                  <td className="py-3 text-slate-300">{stats.calls ?? 0}</td>
                  <td className="py-3 text-slate-300">{stats.errors ?? 0}</td>
                  <td className="py-3 text-slate-300">{(stats.avg_latency_ms ?? 0).toFixed(0)}ms</td>
                  <td className="py-3">
                    <span className={`text-xs ${(stats.error_rate ?? 0) > 0.1 ? "text-red-400" : "text-emerald-400"}`}>
                      {((stats.error_rate ?? 0) * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
              {Object.keys(providerStats).length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-500">No LLM calls made yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
