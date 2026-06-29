import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";

// API base URL — falls back to localhost for local development.
// In production (Vercel), set VITE_API_URL to your Ngrok/backend URL.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_BASE_URL = import.meta.env.VITE_WS_URL ||
  API_BASE_URL.replace(/^https?/, (m) => (m === "https" ? "wss" : "ws"));

const API = axios.create({ baseURL: API_BASE_URL });

// Inject auth token
API.interceptors.request.use((config) => {
  const token = useStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export interface AgentStep {
  agent: string;
  input: string;
  output: string;
  latency_ms: number;
  tokens_used: number;
  provider?: string;
}

export interface EvalMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  overall_score: number;
  passed: boolean;
  retry_count: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  agent_steps: AgentStep[];
  eval_metrics?: EvalMetrics;
  provider_used?: string;
  total_latency_ms: number;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  status: string;
  created_at: string;
  message_count: number;
}

export interface SystemMetrics {
  active_sessions: number;
  total_queries_today: number;
  avg_latency_ms: number;
  provider_distribution: Record<string, number>;
  eval_pass_rate: number;
  error_rate: number;
}

interface Store {
  // Auth
  token: string | null;
  username: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;

  // Sessions
  sessions: Session[];
  activeSession: Session | null;
  fetchSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<Session>;
  setActiveSession: (s: Session) => void;

  // Messages
  messages: Message[];
  isLoading: boolean;
  fetchMessages: (sessionId: string) => Promise<void>;
  sendMessage: (content: string, opts?: {
    enable_rag?: boolean;
    enable_search?: boolean;
    enable_code?: boolean;
  }) => Promise<void>;

  // Streaming
  streamingContent: string;
  isStreaming: boolean;
  wsEventLog: Array<{ type: string; data: unknown }>;

  // Metrics
  metrics: SystemMetrics | null;
  fetchMetrics: () => Promise<void>;
  providerStats: Record<string, unknown>;
  fetchProviderStats: () => Promise<void>;
}

export const useStore = create<Store>()(
  persist(
    (set, get) => ({
      token: null,
      username: null,

      login: async (username, password) => {
        const { data } = await API.post("/api/auth/login", { username, password });
        set({ token: data.access_token, username });
      },

      register: async (username, email, password) => {
        const { data } = await API.post("/api/auth/register", { username, email, password });
        set({ token: data.access_token, username });
      },

      logout: () => set({ token: null, username: null, sessions: [], messages: [], activeSession: null }),

      sessions: [],
      activeSession: null,

      fetchSessions: async () => {
        const { data } = await API.get("/api/sessions/");
        set({ sessions: data });
      },

      createSession: async (title) => {
        const { data } = await API.post("/api/sessions/", { title: title || "New Chat" });
        set((s) => ({ sessions: [data, ...s.sessions], activeSession: data }));
        return data;
      },

      setActiveSession: (session) => {
        set({ activeSession: session, messages: [] });
        get().fetchMessages(session.id);
      },

      messages: [],
      isLoading: false,

      fetchMessages: async (sessionId) => {
        const { data } = await API.get(`/api/messages/${sessionId}`);
        set({ messages: data });
      },

      sendMessage: async (content, opts = {}) => {
        const { activeSession, token } = get();
        if (!activeSession) throw new Error("No active session");

        // Append user message optimistically
        const userMsg: Message = {
          id: `tmp-${Date.now()}`,
          session_id: activeSession.id,
          role: "user",
          content,
          agent_steps: [],
          total_latency_ms: 0,
          created_at: new Date().toISOString(),
        };
        set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

        // Use WebSocket for streaming
        const wsUrl = new URL(`${WS_BASE_URL}/ws/chat/${activeSession.id}`);
        wsUrl.searchParams.set("token", token!);
        wsUrl.searchParams.set("query", content);
        wsUrl.searchParams.set("enable_rag", String(opts.enable_rag ?? true));
        wsUrl.searchParams.set("enable_search", String(opts.enable_search ?? false));
        wsUrl.searchParams.set("enable_code", String(opts.enable_code ?? false));

        set({ streamingContent: "", isStreaming: true, wsEventLog: [] });

        return new Promise((resolve, reject) => {
          const ws = new WebSocket(wsUrl.toString());
          let fullContent = "";

          ws.onmessage = (e) => {
            const event = JSON.parse(e.data);
            set((s) => ({ wsEventLog: [...s.wsEventLog, { type: event.event, data: event.data }] }));

            if (event.event === "stream_token") {
              fullContent += event.data.token;
              set({ streamingContent: fullContent });
            }

            if (event.event === "agent_complete") {
              const assistantMsg: Message = {
                id: `tmp-assistant-${Date.now()}`,
                session_id: activeSession.id,
                role: "assistant",
                content: fullContent,
                agent_steps: event.data.agent_steps || [],
                provider_used: event.data.provider,
                total_latency_ms: event.data.latency_ms,
                created_at: new Date().toISOString(),
              };
              set((s) => ({
                messages: [...s.messages, assistantMsg],
                isLoading: false,
                isStreaming: false,
                streamingContent: "",
              }));
              ws.close();
              resolve();
            }

            if (event.event === "eval_result") {
              set((s) => {
                const msgs = [...s.messages];
                const last = msgs[msgs.length - 1];
                if (last && last.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, eval_metrics: event.data };
                }
                return { messages: msgs };
              });
            }
          };

          ws.onerror = (err) => {
            set({ isLoading: false, isStreaming: false });
            reject(err);
          };

          ws.onclose = () => {
            set({ isStreaming: false });
          };
        });
      },

      streamingContent: "",
      isStreaming: false,
      wsEventLog: [],

      metrics: null,
      fetchMetrics: async () => {
        const { data } = await API.get("/api/metrics/");
        set({ metrics: data });
      },

      providerStats: {},
      fetchProviderStats: async () => {
        const { data } = await API.get("/api/metrics/providers");
        set({ providerStats: data });
      },
    }),
    {
      name: "agentos-store",
      partialize: (state) => ({ token: state.token, username: state.username }),
    }
  )
);
