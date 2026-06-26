import { useEffect, useRef, useState } from "react";
import { useStore, Message } from "../lib/store";
import { Send, Plus, Bot, User, Zap, Search, Code, BarChart3, LogOut, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useNavigate } from "react-router-dom";

const AGENT_COLORS: Record<string, string> = {
  supervisor: "text-yellow-400 bg-yellow-400/10",
  rag: "text-blue-400 bg-blue-400/10",
  search: "text-green-400 bg-green-400/10",
  code: "text-purple-400 bg-purple-400/10",
  synthesizer: "text-orange-400 bg-orange-400/10",
  critic: "text-red-400 bg-red-400/10",
};

const PROVIDER_BADGE: Record<string, string> = {
  azure: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  anthropic: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  google: "bg-green-500/20 text-green-300 border-green-500/30",
};

function EvalBadge({ metrics }: { metrics: NonNullable<Message["eval_metrics"]> }) {
  const color = metrics.passed ? "text-emerald-400" : "text-red-400";
  return (
    <div className="mt-2 flex items-center gap-3 text-xs">
      <span className={`font-mono font-bold ${color}`}>
        {metrics.passed ? "✓ EVAL PASS" : "✗ EVAL FAIL"}
      </span>
      <span className="text-slate-500">
        F:{(metrics.faithfulness * 100).toFixed(0)}%
        · R:{(metrics.answer_relevancy * 100).toFixed(0)}%
        · P:{(metrics.context_precision * 100).toFixed(0)}%
      </span>
      {metrics.retry_count > 0 && (
        <span className="text-yellow-400">{metrics.retry_count} retries</span>
      )}
    </div>
  );
}

function AgentTrace({ steps }: { steps: Message["agent_steps"] }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <ChevronRight size={12} className={`transition-transform ${open ? "rotate-90" : ""}`} />
        {steps.length} agent steps
      </button>
      {open && (
        <div className="mt-2 space-y-1.5 pl-3 border-l border-slate-700">
          {steps.map((step, i) => (
            <div key={i} className="text-xs">
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold mr-2 ${AGENT_COLORS[step.agent] || "text-slate-400 bg-slate-800"}`}>
                {step.agent}
              </span>
              <span className="text-slate-400">{step.output.slice(0, 80)}</span>
              <span className="text-slate-600 ml-2">{step.latency_ms.toFixed(0)}ms</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg, isStreaming, streamContent }: {
  msg: Message;
  isStreaming?: boolean;
  streamContent?: string;
}) {
  const isUser = msg.role === "user";
  const content = isStreaming ? streamContent || "" : msg.content;

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? "bg-indigo-600" : "bg-slate-700"}`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div className={`rounded-2xl px-4 py-3 ${isUser
          ? "bg-indigo-600 text-white rounded-tr-sm"
          : "bg-slate-800 text-slate-100 rounded-tl-sm"
        }`}>
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{content}</ReactMarkdown>
              {isStreaming && <span className="inline-block w-1.5 h-4 bg-indigo-400 animate-pulse ml-0.5" />}
            </div>
          )}
        </div>

        {!isUser && !isStreaming && (
          <div className="px-1 mt-1">
            {msg.provider_used && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${PROVIDER_BADGE[msg.provider_used] || "text-slate-500 bg-slate-800 border-slate-700"}`}>
                {msg.provider_used} · {msg.total_latency_ms.toFixed(0)}ms
              </span>
            )}
            <AgentTrace steps={msg.agent_steps} />
            {msg.eval_metrics && <EvalBadge metrics={msg.eval_metrics} />}
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatPage() {
  const navigate = useNavigate();
  const {
    sessions, activeSession, messages, isLoading, isStreaming, streamingContent,
    fetchSessions, createSession, setActiveSession, sendMessage, logout
  } = useStore();

  const [input, setInput] = useState("");
  const [enableRag, setEnableRag] = useState(true);
  const [enableSearch, setEnableSearch] = useState(false);
  const [enableCode, setEnableCode] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchSessions(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    let session = activeSession;
    if (!session) {
      session = await createSession(input.slice(0, 40));
    }
    const q = input;
    setInput("");
    await sendMessage(q, { enable_rag: enableRag, enable_search: enableSearch, enable_code: enableCode });
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Zap size={14} />
            </div>
            <span className="font-bold text-base tracking-tight">AgentOS</span>
          </div>
          <button
            onClick={() => createSession()}
            className="w-full flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={16} /> New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveSession(s)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors truncate ${
                activeSession?.id === s.id
                  ? "bg-slate-700 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {s.title}
              <span className="block text-[11px] text-slate-600 mt-0.5">{s.message_count} messages</span>
            </button>
          ))}
        </div>

        <div className="p-3 border-t border-slate-800 space-y-1">
          <button onClick={() => navigate("/dashboard")} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors">
            <BarChart3 size={15} /> Dashboard
          </button>
          <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-indigo-600/20 rounded-2xl flex items-center justify-center mb-4">
                <Zap size={32} className="text-indigo-400" />
              </div>
              <h2 className="text-2xl font-bold text-slate-200 mb-2">AgentOS</h2>
              <p className="text-slate-500 max-w-sm text-sm">
                Multi-agent RAG platform. Ask anything — enable Search for real-time data, Code for execution.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}

          {isStreaming && (
            <MessageBubble
              msg={{
                id: "streaming",
                session_id: activeSession?.id || "",
                role: "assistant",
                content: "",
                agent_steps: [],
                total_latency_ms: 0,
                created_at: "",
              }}
              isStreaming
              streamContent={streamingContent}
            />
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-slate-800 p-4">
          {/* Tool toggles */}
          <div className="flex items-center gap-2 mb-3">
            {[
              { icon: Zap, label: "RAG", state: enableRag, setter: setEnableRag },
              { icon: Search, label: "Search", state: enableSearch, setter: setEnableSearch },
              { icon: Code, label: "Code", state: enableCode, setter: setEnableCode },
            ].map(({ icon: Icon, label, state, setter }) => (
              <button
                key={label}
                onClick={() => setter(!state)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  state
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>

          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Ask anything... (Shift+Enter for new line)"
              rows={2}
              disabled={isLoading || isStreaming}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:border-indigo-500 disabled:opacity-50 transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading || isStreaming}
              className="px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-white transition-colors"
            >
              {isLoading || isStreaming ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Send size={18} />
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
