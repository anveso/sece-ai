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
  is_approved: boolean;
  created_at: string;
}

export interface AdminUser extends User {
  conversation_count: number;
  message_count: number;
  last_active: string | null;
}

export interface AdminDocumentItem extends DocumentItem {
  owner_email: string;
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
  is_shared: boolean;
  created_at: string;
}

export interface AgentInfo {
  key: string;
  name: string;
  description: string;
  group: string;
}

// Extracts FastAPI's {"detail": "..."} message from an error response body,
// falling back to the raw text if it's not JSON-shaped - used by login/
// register so the UI can show the real reason (e.g. "pending admin
// approval") instead of a generic failure message.
async function errorDetail(res: Response, fallback: string): Promise<string> {
  const text = await res.text();
  try {
    const parsed = JSON.parse(text);
    return parsed.detail || fallback;
  } catch {
    return text || fallback;
  }
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
  if (!res.ok) throw new Error(await errorDetail(res, "Invalid email or password"));
  const data = await res.json();
  setToken(data.access_token);
  return data.user as User;
}

// Self-service registration no longer logs the account in - new accounts
// need admin approval first (see backend/app/routers/auth.py), so there's
// no valid session to hand back yet. Returns the server's message plus the
// created user record; the caller (login/page.tsx) shows the message
// instead of navigating to /chat.
export async function register(email: string, password: string, full_name: string) {
  // No role field here on purpose - self-service registration always
  // creates a "student" account server-side regardless of what's sent
  // (see backend/app/routers/auth.py). Admin accounts are promoted
  // manually, never picked at signup.
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Registration failed"));
  const data = await res.json();
  return data as { message: string; user: User };
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

export async function uploadDocument(
  file: File,
  shared: boolean = false
): Promise<DocumentItem> {
  const form = new FormData();
  form.append("file", file);
  form.append("shared", String(shared));
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

// --- Admin (all 403 server-side for non-admin accounts, see
// backend/app/routers/admin.py's require_admin) ---

export async function adminListUsers(): Promise<AdminUser[]> {
  const res = await authFetch("/admin/users");
  return res.json();
}

export async function adminApproveUser(userId: string): Promise<AdminUser> {
  const res = await authFetch(`/admin/users/${userId}/approve`, { method: "POST" });
  return res.json();
}

export async function adminSetUserRole(
  userId: string,
  role: string
): Promise<AdminUser> {
  const res = await authFetch(`/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  return res.json();
}

export async function adminDeleteUser(userId: string) {
  await authFetch(`/admin/users/${userId}`, { method: "DELETE" });
}

export async function adminListDocuments(): Promise<AdminDocumentItem[]> {
  const res = await authFetch("/admin/documents");
  return res.json();
}
