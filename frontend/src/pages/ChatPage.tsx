import { useEffect, useRef, useState } from "react";
import { useStore, type Message } from "../lib/store";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";

/* ── Icons ────────────────────────────────────────────────────────── */
const Icon = {
  Bolt: () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
  Plus: () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  User: () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>,
  Bot:  () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M12 11V7m-4-3h8M7 7h.01M17 7h.01"/><circle cx="9" cy="16" r="1" fill="currentColor"/><circle cx="15" cy="16" r="1" fill="currentColor"/></svg>,
  Send: () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>,
  Search: () => <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  Code: () => <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  Bar:  () => <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
  Out:  () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  Chev:() => <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>,
  Trash:()=> <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>,
};

/* ── Agent colours ────────────────────────────────────────────────── */
const AGENT_STYLE: Record<string, { bg: string; color: string }> = {
  supervisor: { bg: "rgba(245,158,11,0.12)",  color: "#F59E0B" },
  gather:     { bg: "rgba(52,211,153,0.12)",  color: "#34D399" },
  rag:        { bg: "rgba(96,165,250,0.12)",  color: "#60A5FA" },
  search:     { bg: "rgba(52,211,153,0.12)",  color: "#34D399" },
  code:       { bg: "rgba(167,139,250,0.12)", color: "#A78BFA" },
  synthesizer:{ bg: "rgba(251,146,60,0.12)",  color: "#FB923C" },
  critic:     { bg: "rgba(244,63,94,0.12)",   color: "#F43F5E" },
};

const PROVIDER_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  azure:     { color: "#60A5FA", bg: "rgba(96,165,250,0.08)",  border: "rgba(96,165,250,0.2)" },
  anthropic: { color: "#FB923C", bg: "rgba(251,146,60,0.08)",  border: "rgba(251,146,60,0.2)" },
  google:    { color: "#34D399", bg: "rgba(52,211,153,0.08)",  border: "rgba(52,211,153,0.2)" },
};

/* ── Sub-components ───────────────────────────────────────────────── */
function AgentStepBadge({ agent }: { agent: string }) {
  const s = AGENT_STYLE[agent] ?? { bg: "rgba(148,163,196,0.1)", color: "#94A3C4" };
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-medium"
      style={{ background: s.bg, color: s.color }}>
      {agent}
    </span>
  );
}

function AgentTrace({ steps }: { steps: Message["agent_steps"] }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs transition-colors duration-150 group"
        style={{ color: "var(--text-3)" }}>
        <span className="transition-transform duration-200 inline-block" style={{ transform: open ? "rotate(90deg)" : "rotate(0)" }}>
          <Icon.Chev />
        </span>
        <span className="group-hover:text-t2 transition-colors">{steps.length} agent steps</span>
      </button>
      {open && (
        <div className="mt-2.5 space-y-1.5 pl-3 animate-fade-in"
          style={{ borderLeft: "1px solid var(--border-md)" }}>
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <AgentStepBadge agent={s.agent} />
              <span className="truncate flex-1" style={{ color: "var(--text-3)" }}>{s.output?.slice(0, 72)}</span>
              <span className="font-mono shrink-0" style={{ color: "var(--text-4)", fontSize: 10 }}>{s.latency_ms.toFixed(0)}ms</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EvalBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#10B981" : pct >= 65 ? "#F59E0B" : "#F43F5E";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] w-8 shrink-0" style={{ color: "var(--text-3)", fontFamily: "monospace" }}>{label}</span>
      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: "var(--surface-c)" }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[10px] font-mono w-7 text-right" style={{ color }}>{pct}%</span>
    </div>
  );
}

function EvalPanel({ metrics }: { metrics: NonNullable<Message["eval_metrics"]> }) {
  const [open, setOpen] = useState(false);
  const passed = metrics.passed;
  const score = Math.round(metrics.overall_score * 100);
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-xs"
        style={{ color: passed ? "#10B981" : "#F43F5E" }}>
        <span className="font-mono font-semibold">
          {passed ? "✓ EVAL PASS" : "✗ EVAL FAIL"}
        </span>
        <span className="font-mono" style={{ color: "var(--text-3)" }}>
          {score}/100
        </span>
        {metrics.retry_count > 0 && (
          <span className="px-1.5 py-0.5 rounded text-[10px]"
            style={{ background: "rgba(245,158,11,0.12)", color: "#F59E0B" }}>
            {metrics.retry_count} retr{metrics.retry_count > 1 ? "ies" : "y"}
          </span>
        )}
      </button>
      {open && (
        <div className="mt-2 space-y-1.5 animate-fade-in">
          <EvalBar label="F" value={metrics.faithfulness} />
          <EvalBar label="R" value={metrics.answer_relevancy} />
          <EvalBar label="P" value={metrics.context_precision} />
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg, streaming, streamContent }: {
  msg: Message; streaming?: boolean; streamContent?: string;
}) {
  const isUser = msg.role === "user";
  const content = streaming ? streamContent ?? "" : msg.content;
  const pStyle = msg.provider_used ? PROVIDER_STYLE[msg.provider_used] : undefined;

  return (
    <div className={`flex gap-3 animate-fade-up ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className="shrink-0 mt-0.5">
        <div className="w-8 h-8 rounded-full flex items-center justify-center"
          style={isUser
            ? { background: "linear-gradient(135deg, var(--accent), var(--violet))" }
            : { background: "var(--surface-c)", border: "1px solid var(--border-md)" }
          }>
          {isUser ? <Icon.User /> : <Icon.Bot />}
        </div>
      </div>

      {/* Content */}
      <div className={`flex flex-col max-w-[78%] ${isUser ? "items-end" : "items-start"}`}>
        <div className="rounded-2xl px-4 py-3"
          style={isUser
            ? { background: "linear-gradient(135deg, var(--accent), var(--violet))", color: "#fff", borderTopRightRadius: 4 }
            : { background: "var(--surface-b)", border: "1px solid var(--border)", color: "var(--text-1)", borderTopLeftRadius: 4 }
          }>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose-chat text-sm">
              <ReactMarkdown>{content}</ReactMarkdown>
              {streaming && <span className="inline-block w-0.5 h-4 ml-0.5 align-text-bottom cursor-blink"
                style={{ background: "var(--accent)" }} />}
            </div>
          )}
        </div>

        {/* Metadata row */}
        {!isUser && !streaming && (
          <div className="mt-1.5 px-1 w-full">
            {pStyle && msg.provider_used && (
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md border"
                  style={{ background: pStyle.bg, color: pStyle.color, borderColor: pStyle.border }}>
                  {msg.provider_used}
                </span>
                <span className="text-[10px] font-mono" style={{ color: "var(--text-4)" }}>
                  {msg.total_latency_ms.toFixed(0)}ms
                </span>
              </div>
            )}
            <AgentTrace steps={msg.agent_steps} />
            {msg.eval_metrics && <EvalPanel metrics={msg.eval_metrics} />}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
        style={{ background: "var(--surface-c)", border: "1px solid var(--border-md)" }}>
        <Icon.Bot />
      </div>
      <div className="rounded-2xl px-4 py-3 flex items-center gap-1.5"
        style={{ background: "var(--surface-b)", border: "1px solid var(--border)", borderTopLeftRadius: 4 }}>
        {[0, 1, 2].map(i => (
          <div key={i} className="w-1.5 h-1.5 rounded-full"
            style={{
              background: "var(--accent)",
              animation: `pulse-dot 1.2s ease ${i * 0.2}s infinite`,
            }} />
        ))}
      </div>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────────────── */
export function ChatPage() {
  const navigate = useNavigate();
  const {
    sessions, activeSession, messages, isLoading, isStreaming, streamingContent,
    username, fetchSessions, createSession, setActiveSession, sendMessage, logout,
  } = useStore();

  const [input, setInput] = useState("");
  const [enableRag, setEnableRag] = useState(true);
  const [enableSearch, setEnableSearch] = useState(false);
  const [enableCode, setEnableCode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { fetchSessions(); }, []);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading || isStreaming) return;
    let session = activeSession;
    if (!session) session = await createSession(input.slice(0, 48));
    const q = input.trim();
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await sendMessage(q, { enable_rag: enableRag, enable_search: enableSearch, enable_code: enableCode });
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const tools = [
    { key: "rag",    label: "RAG",    icon: <Icon.Bolt />,   state: enableRag,    set: setEnableRag },
    { key: "search", label: "Search", icon: <Icon.Search />, state: enableSearch, set: setEnableSearch },
    { key: "code",   label: "Code",   icon: <Icon.Code />,   state: enableCode,   set: setEnableCode },
  ];

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--base)" }}>

      {/* ── Sidebar ── */}
      <aside className={`${sidebarOpen ? "w-64" : "w-0 overflow-hidden"} transition-all duration-300 flex flex-col shrink-0`}
        style={{ background: "var(--surface-a)", borderRight: "1px solid var(--border)" }}>

        {/* Header */}
        <div className="p-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: "linear-gradient(135deg, var(--accent), var(--violet))" }}>
              <Icon.Bolt />
            </div>
            <span className="font-semibold text-sm tracking-tight" style={{ color: "var(--text-1)" }}>AgentOS</span>
          </div>
          <button onClick={() => createSession()}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 hover:opacity-90 active:scale-[0.98]"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--violet))", color: "#fff",
              boxShadow: "0 4px 16px rgba(108,99,255,0.3)" }}>
            <Icon.Plus /> New chat
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.length === 0 && (
            <p className="text-xs text-center mt-6" style={{ color: "var(--text-4)" }}>No conversations yet</p>
          )}
          {sessions.map(s => (
            <button key={s.id} onClick={() => setActiveSession(s)}
              className="w-full text-left px-3 py-2.5 rounded-xl mb-1 transition-all duration-150 group relative"
              style={activeSession?.id === s.id
                ? { background: "var(--surface-c)", border: "1px solid var(--border-md)" }
                : { background: "transparent", border: "1px solid transparent" }
              }>
              {activeSession?.id === s.id && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r"
                  style={{ background: "var(--accent)" }} />
              )}
              <p className="text-xs truncate font-medium"
                style={{ color: activeSession?.id === s.id ? "var(--text-1)" : "var(--text-2)" }}>
                {s.title}
              </p>
              <p className="text-[10px] mt-0.5" style={{ color: "var(--text-4)" }}>
                {s.message_count} messages
              </p>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 space-y-0.5" style={{ borderTop: "1px solid var(--border)" }}>
          {username && (
            <div className="flex items-center gap-2 px-3 py-2 mb-1">
              <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold"
                style={{ background: "var(--accent-dim)", color: "var(--accent-hi)" }}>
                {username[0]?.toUpperCase()}
              </div>
              <span className="text-xs font-medium truncate" style={{ color: "var(--text-2)" }}>{username}</span>
            </div>
          )}
          {[
            { icon: <Icon.Bar />,  label: "Dashboard", action: () => navigate("/dashboard") },
            { icon: <Icon.Out />,  label: "Sign out",  action: logout },
          ].map(({ icon, label, action }) => (
            <button key={label} onClick={action}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-all duration-150 hover:bg-surf-c"
              style={{ color: "var(--text-3)" }}>
              {icon} {label}
            </button>
          ))}
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col min-w-0">

        {/* Topbar */}
        <header className="flex items-center gap-3 px-4 h-14 shrink-0"
          style={{ borderBottom: "1px solid var(--border)", background: "rgba(7,11,20,0.8)", backdropFilter: "blur(12px)" }}>
          <button onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: "var(--text-3)" }}>
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div className="flex-1 min-w-0">
            {activeSession && (
              <p className="text-sm font-medium truncate" style={{ color: "var(--text-2)" }}>
                {activeSession.title}
              </p>
            )}
          </div>
          {/* Provider health pills */}
          <div className="flex items-center gap-1.5">
            {[["azure","#60A5FA"],["anthropic","#FB923C"],["google","#34D399"]].map(([name, color]) => (
              <div key={name} className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-mono"
                style={{ background: "var(--surface-b)", border: "1px solid var(--border)", color }}>
                <div className="w-1 h-1 rounded-full" style={{ background: color, animation: "pulse-dot 2s ease infinite" }} />
                {name}
              </div>
            ))}
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
          <div className="max-w-3xl mx-auto space-y-5">
            {messages.length === 0 && !isLoading && !isStreaming ? (
              <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center animate-fade-in">
                <div className="relative mb-6">
                  <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
                    style={{ background: "linear-gradient(135deg, var(--accent-dim), var(--violet-dim))",
                      border: "1px solid var(--border-md)" }}>
                    <svg width="36" height="36" fill="none" stroke="url(#g)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                      <defs>
                        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#6C63FF"/>
                          <stop offset="100%" stopColor="#8B5CF6"/>
                        </linearGradient>
                      </defs>
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                  </div>
                </div>
                <h2 className="text-2xl font-semibold mb-2" style={{ color: "var(--text-1)" }}>
                  How can I help?
                </h2>
                <p className="text-sm max-w-xs leading-relaxed" style={{ color: "var(--text-3)" }}>
                  Ask anything. Enable Search for live web data or Code to run Python in a sandbox.
                </p>
                <div className="flex gap-2 mt-6 flex-wrap justify-center">
                  {["Explain LangGraph state machines","Compare LLM providers","How does RAG retrieval work?"].map(q => (
                    <button key={q} onClick={() => setInput(q)}
                      className="text-xs px-4 py-2.5 rounded-xl transition-all duration-150 hover:border-accent"
                      style={{ background: "var(--surface-b)", border: "1px solid var(--border-md)", color: "var(--text-2)" }}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
                {isLoading && !isStreaming && <TypingIndicator />}
                {isStreaming && (
                  <MessageBubble
                    msg={{ id: "s", session_id: "", role: "assistant", content: "", agent_steps: [], total_latency_ms: 0, created_at: "" }}
                    streaming streamContent={streamingContent}
                  />
                )}
              </>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input dock */}
        <div className="px-4 md:px-8 pb-5 pt-3 shrink-0"
          style={{ borderTop: "1px solid var(--border)", background: "rgba(7,11,20,0.9)", backdropFilter: "blur(16px)" }}>
          <div className="max-w-3xl mx-auto">
            {/* Tool toggles */}
            <div className="flex items-center gap-2 mb-3">
              {tools.map(({ key, label, icon, state, set }) => (
                <button key={key} onClick={() => set(!state)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150"
                  style={state
                    ? { background: "var(--accent-dim)", color: "var(--accent-hi)", border: "1px solid rgba(108,99,255,0.3)" }
                    : { background: "var(--surface-b)", color: "var(--text-3)", border: "1px solid var(--border)" }
                  }>
                  {icon} {label}
                </button>
              ))}
            </div>

            {/* Textarea + send */}
            <div className="relative rounded-2xl overflow-hidden transition-all duration-200"
              style={{ background: "var(--surface-b)", border: "1px solid var(--border-md)" }}
              onFocusCapture={e => (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(108,99,255,0.5)"}
              onBlurCapture={e => (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-md)"}>
              <textarea ref={textareaRef} value={input} onChange={handleTextareaInput}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder="Ask anything… (Shift+Enter for new line)"
                rows={1}
                disabled={isLoading || isStreaming}
                className="w-full px-4 pt-3.5 pb-12 text-sm resize-none outline-none bg-transparent leading-relaxed disabled:opacity-50"
                style={{ color: "var(--text-1)", maxHeight: 160 }}
              />
              {/* Bottom bar inside textarea */}
              <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-4 pb-3">
                <span className="text-[10px] font-mono" style={{ color: "var(--text-4)" }}>
                  {input.length > 0 ? `${input.length} chars` : "Enter to send · Shift+Enter for newline"}
                </span>
                <button onClick={handleSend}
                  disabled={!input.trim() || isLoading || isStreaming}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-medium transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed active:scale-95"
                  style={{ background: "linear-gradient(135deg, var(--accent), var(--violet))", color: "#fff",
                    boxShadow: input.trim() ? "0 4px 16px rgba(108,99,255,0.4)" : "none" }}>
                  {isLoading || isStreaming
                    ? <svg className="animate-spin" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-6.219-8.56" strokeLinecap="round"/></svg>
                    : <Icon.Send />
                  }
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
