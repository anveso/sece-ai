export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("sece_ai_token");
}

export function setToken(token: string) {
  window.localStorage.setItem("sece_ai_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("sece_ai_token");
}

async function authFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

export interface Conversation {
  id: string;
  title: string;
  agent: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  agent: string | null;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string | null;
  status: "processing" | "ready" | "error";
  error_message: string | null;
  created_at: string;
}

export interface AgentInfo {
  key: string;
  name: string;
  description: string;
}

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) throw new Error("Invalid email or password");
  const data = await res.json();
  setToken(data.access_token);
  return data.user as User;
}

export async function register(
  email: string,
  password: string,
  full_name: string,
  role: string
) {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name, role }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  setToken(data.access_token);
  return data.user as User;
}

export async function fetchMe(): Promise<User> {
  const res = await authFetch("/auth/me");
  return res.json();
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await authFetch("/conversations");
  return res.json();
}

export async function getConversation(id: string) {
  const res = await authFetch(`/conversations/${id}`);
  return res.json();
}

export async function deleteConversation(id: string) {
  await authFetch(`/conversations/${id}`, { method: "DELETE" });
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const res = await authFetch("/documents");
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const form = new FormData();
  form.append("file", file);
  const res = await authFetch("/documents", { method: "POST", body: form });
  return res.json();
}

export async function deleteDocument(id: string) {
  await authFetch(`/documents/${id}`, { method: "DELETE" });
}

export async function listAgents(): Promise<AgentInfo[]> {
  const res = await authFetch("/agents");
  return res.json();
}

/**
 * Streams an assistant reply token-by-token via Server-Sent Events.
 * `agent` is only used when starting a brand-new conversation (it's ignored
 * server-side otherwise). onAgent fires once, before the first token, with
 * whichever specialist agent the router (or the pinned conversation agent)
 * resolved to - use it to show a "Research Agent" style badge immediately.
 */
export async function streamChat(
  message: string,
  conversationId: string | null,
  agent: string,
  onToken: (token: string) => void,
  onAgent: (key: string, name: string) => void,
  onDone: (conversationId: string) => void,
  onError: (message: string) => void
) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      agent,
    }),
  });

  if (!res.ok || !res.body) {
    onError(await res.text());
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let activeConversationId = conversationId || "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const raw of events) {
      const lines = raw.split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7);
        if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (!data) continue;
      const parsed = JSON.parse(data);

      if (event === "start") activeConversationId = parsed.conversation_id;
      if (event === "agent") onAgent(parsed.key, parsed.name);
      if (event === "token") onToken(parsed.content);
      if (event === "error") onError(parsed.detail);
      if (event === "done") onDone(activeConversationId);
    }
  }
}
