const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type UserProfile = {
  id: string;
  name: string;
  department: string;
  sap_id: string;
  phone: string;
  email: string;
};

export type AgentListItem = {
  id: string;
  name: string;
  visibility: string;
};

export type AgentPublicInfo = {
  id: string;
  name: string;
  visibility: string;
  config: Record<string, unknown>;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  tokens_used: number;
  created_at: string;
};

export type ConversationSummary = {
  id: string;
  agent_id: string;
  agent_name: string;
  created_at: string;
  last_active_at: string;
  message_count: number;
  last_message: string;
};

export type ConversationResponse = {
  id: string;
  agent_id: string;
  agent_name: string;
  created_at: string;
  last_active_at: string;
  messages: Message[];
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
  });
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("认证失效，请重新登录");
  }
  return res;
}

// ── Auth ──
export async function register(body: {
  name: string; department: string; sap_id: string;
  phone: string; email: string; password: string;
}) {
  const res = await apiFetch("/auth/register", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) throw new Error((await res.json()).detail || "注册失败");
  return res.json();
}

export async function login(account: string, password: string) {
  const res = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ account, password }) });
  if (!res.ok) throw new Error((await res.json()).detail || "登录失败");
  const data = await res.json();
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  if (typeof window !== "undefined") window.location.href = "/login";
}

export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

export async function getProfile(): Promise<UserProfile> {
  const res = await apiFetch("/auth/profile");
  if (!res.ok) throw new Error((await res.json()).detail || "获取用户信息失败");
  return res.json();
}

// ── Agents ──
export async function listAccessibleAgents(): Promise<AgentListItem[]> {
  const res = await apiFetch("/chat/agents");
  if (!res.ok) throw new Error((await res.json()).detail || "获取 Agent 列表失败");
  return res.json();
}

// ── Conversations ──
export async function getConversations(): Promise<ConversationSummary[]> {
  const res = await apiFetch("/chat/conversations");
  if (!res.ok) throw new Error((await res.json()).detail || "获取会话失败");
  return res.json();
}

export async function getConversation(convId: string): Promise<ConversationResponse> {
  const res = await apiFetch(`/chat/conversations/${convId}`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取会话失败");
  return res.json();
}

export async function createConversation(agentId: string): Promise<ConversationResponse> {
  const res = await apiFetch(`/chat/agents/${agentId}/conversations`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json()).detail || "创建会话失败");
  return res.json();
}

// ── Chat ──
export async function getAgentByLink(linkCode: string): Promise<AgentPublicInfo> {
  const res = await apiFetch(`/chat/agent/${linkCode}`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取 Agent 失败");
  return res.json();
}

export async function sendMessage(
  linkCode: string,
  content: string,
): Promise<Message> {
  const res = await apiFetch(`/chat/agent/${linkCode}/messages`, {
    method: "POST",
    body: JSON.stringify({ content, stream: false }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "发送失败");
  return res.json();
}

export async function sendMessageToConv(
  convId: string,
  content: string,
): Promise<Message> {
  // Use the send message API with a share link approach
  // We need the link_code for chat; for now use the conv-based send
  const res = await apiFetch(`/chat/conversations/${convId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content, stream: false }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "发送失败");
  return res.json();
}

// ── Link code lookup ──
export async function getLinkCodeForAgent(agentId: string): Promise<string> {
  // We need a share link to send messages. Find any active link for this agent.
  // For the main chat page, we'll use the agent ID directly with a new endpoint approach.
  // Simplified: use the agent's first active share link, or create one.
  const res = await apiFetch(`/chat/agent/${agentId}/link`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取链接失败");
  const data = await res.json();
  return data.link_code;
}
