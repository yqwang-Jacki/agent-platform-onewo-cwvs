const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type Agent = {
  id: string;
  appid: string;
  name: string;
  config: Record<string, unknown>;
  visibility: "public" | "department" | "specific";
  permission_config: Record<string, unknown> | null;
  api_endpoint: string;
  api_headers: Record<string, string>;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ShareLink = {
  id: string;
  link_code: string;
  status: string;
  expire_at: string | null;
  created_at: string;
  share_url: string;
};

export type TokenStat = {
  agent_id: string;
  total_tokens: number;
  total_requests: number;
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("publisher_access_token");
}

export function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("publisher_access_token");
}

export function logout() {
  localStorage.removeItem("publisher_access_token");
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

export async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
  });
  if (res.status === 401) {
    logout();
    throw new Error("认证失效，请重新登录");
  }
  return res;
}

export async function loginPublisher(account: string, password: string) {
  const res = await apiFetch("/publisher/web-login", {
    method: "POST",
    body: JSON.stringify({ account, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "登录失败");
  const data = await res.json();
  localStorage.setItem("publisher_access_token", data.access_token);
  if (data.user_name) localStorage.setItem("admin_user_name", data.user_name);
  if (data.user_role) localStorage.setItem("admin_user_role", data.user_role);
  return data;
}

export async function listAgents(): Promise<Agent[]> {
  const res = await apiFetch("/publisher/agents");
  if (!res.ok) throw new Error((await res.json()).detail || "获取 Agent 列表失败");
  return res.json();
}

export async function createAgent(body: Omit<Agent, "id" | "appid" | "status" | "created_at" | "updated_at">): Promise<Agent> {
  const res = await apiFetch("/publisher/agents", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "创建 Agent 失败");
  return res.json();
}

export async function updateAgent(id: string, body: Partial<Agent>): Promise<Agent> {
  const res = await apiFetch(`/publisher/agents/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "更新 Agent 失败");
  return res.json();
}

export async function deleteAgent(id: string) {
  const res = await apiFetch(`/publisher/agents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json()).detail || "删除 Agent 失败");
}

export async function createLink(agentId: string, expireDays?: number): Promise<ShareLink> {
  const res = await apiFetch(`/publisher/agents/${agentId}/links`, {
    method: "POST",
    body: JSON.stringify({ expire_days: expireDays }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "创建链接失败");
  return res.json();
}

export async function listLinks(agentId: string): Promise<ShareLink[]> {
  const res = await apiFetch(`/publisher/agents/${agentId}/links`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取链接失败");
  return res.json();
}

export async function revokeLink(linkId: string) {
  const res = await apiFetch(`/publisher/agents/links/${linkId}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json()).detail || "失效链接失败");
}

export async function getTokenStats(): Promise<TokenStat[]> {
  const res = await apiFetch("/publisher/agents/stats/tokens");
  if (!res.ok) throw new Error((await res.json()).detail || "获取用量统计失败");
  return res.json();
}

// ── Admin: User & Role Management ──────────────────

export type AdminUser = {
  id: string;
  name: string;
  department: string;
  sap_id: string;
  phone: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
  last_login_at: string | null;
};

export type RoleInfo = {
  key: string;
  label: string;
  level: number;
  permissions: string[];
};

export type RoleItem = {
  id: string;
  key: string;
  label: string;
  description: string;
  level: number;
  permissions: string[];
  is_system: boolean;
  status: string;
  created_at: string;
};

export type MenuPermission = {
  key: string;
  label: string;
  category: string;
};

export type PublisherInfo = {
  appid: string;
  name: string;
  phone: string;
  status: string;
  created_at: string;
};

export function parseUserFromToken(): { name: string; role: string } | null {
  if (typeof window === "undefined") return null;
  const t = getToken();
  if (!t) return null;
  try {
    const payload = JSON.parse(atob(t.split(".")[1]));
    return { name: "", role: payload.role || "user" };
  } catch { return null; }
}

export function getUserRole(): string {
  return parseUserFromToken()?.role || "user";
}

export async function listAdminUsers(params?: { role?: string; status?: string; search?: string }): Promise<AdminUser[]> {
  const sp = new URLSearchParams();
  if (params?.role) sp.set("role", params.role);
  if (params?.status) sp.set("status", params.status);
  if (params?.search) sp.set("search", params.search);
  const qs = sp.toString();
  const res = await apiFetch(`/admin/users${qs ? "?" + qs : ""}`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取用户列表失败");
  return res.json();
}

export async function getUserById(userId: string): Promise<AdminUser> {
  const res = await apiFetch(`/admin/users/${userId}`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取用户详情失败");
  return res.json();
}

export async function updateUserRole(userId: string, role: string): Promise<AdminUser> {
  const res = await apiFetch(`/admin/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "修改角色失败");
  return res.json();
}

export async function updateUserStatus(userId: string, status: string): Promise<AdminUser> {
  const res = await apiFetch(`/admin/users/${userId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "修改状态失败");
  return res.json();
}

export async function resetUserPassword(userId: string): Promise<{ message: string; new_password: string }> {
  const res = await apiFetch(`/admin/users/${userId}/reset-password`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json()).detail || "重置密码失败");
  return res.json();
}

export async function listRoles(): Promise<RoleItem[]> {
  const res = await apiFetch("/admin/roles");
  if (!res.ok) throw new Error((await res.json()).detail || "获取角色列表失败");
  return res.json();
}

export async function getRoleById(roleId: string): Promise<RoleItem> {
  const res = await apiFetch(`/admin/roles/${roleId}`);
  if (!res.ok) throw new Error((await res.json()).detail || "获取角色详情失败");
  return res.json();
}

export async function createRole(data: { key: string; label: string; description: string; level: number; permissions: string[] }): Promise<RoleItem> {
  const res = await apiFetch("/admin/roles", { method: "POST", body: JSON.stringify(data) });
  if (!res.ok) throw new Error((await res.json()).detail || "创建角色失败");
  return res.json();
}

export async function updateRole(roleId: string, data: { label?: string; description?: string; level?: number; permissions?: string[] }): Promise<RoleItem> {
  const res = await apiFetch(`/admin/roles/${roleId}`, { method: "PUT", body: JSON.stringify(data) });
  if (!res.ok) throw new Error((await res.json()).detail || "更新角色失败");
  return res.json();
}

export async function deleteRole(roleId: string): Promise<{ message: string }> {
  const res = await apiFetch(`/admin/roles/${roleId}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json()).detail || "删除角色失败");
  return res.json();
}

export async function updateUser(userId: string, data: { name?: string; department?: string; sap_id?: string; phone?: string; email?: string; role?: string; status?: string }): Promise<AdminUser> {
  const res = await apiFetch(`/admin/users/${userId}`, { method: "PUT", body: JSON.stringify(data) });
  if (!res.ok) throw new Error((await res.json()).detail || "更新用户失败");
  return res.json();
}

export async function createUser(data: { name: string; department: string; sap_id: string; phone: string; email: string; password: string; role: string }): Promise<AdminUser> {
  const res = await apiFetch("/admin/users", { method: "POST", body: JSON.stringify(data) });
  if (!res.ok) throw new Error((await res.json()).detail || "创建用户失败");
  return res.json();
}

export async function deleteUser(userId: string): Promise<{ message: string }> {
  const res = await apiFetch(`/admin/users/${userId}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json()).detail || "删除用户失败");
  return res.json();
}

export async function listMenus(): Promise<MenuPermission[]> {
  const res = await apiFetch("/admin/menus");
  if (!res.ok) throw new Error((await res.json()).detail || "获取菜单列表失败");
  return res.json();
}

export async function listAdminPublishers(): Promise<PublisherInfo[]> {
  const res = await apiFetch("/admin/publishers");
  if (!res.ok) throw new Error((await res.json()).detail || "获取发布者列表失败");
  return res.json();
}

// ── Platform Connector APIs ──────────────────────

export type PlatformInfo = {
  platform_type: string;
  label: string;
  icon: string;
  help_text: string;
};

export type PlatformBotItem = {
  bot_id: string;
  name: string;
  description: string;
  platform_type: string;
};

export type PlatformImportRequest = {
  platform_type: string;
  appid?: string;
  secret_key?: string;
  api_token?: string;
  client_id?: string;
  client_secret?: string;
  domain?: string;
  project_id?: number;
  bot_id?: string;
  bot_name?: string;
  name: string;
  visibility: string;
  permission_config?: Record<string, unknown> | null;
  config?: Record<string, unknown>;
};

export async function listPlatforms(): Promise<PlatformInfo[]> {
  const res = await apiFetch("/platforms");
  if (!res.ok) throw new Error((await res.json()).detail || "获取平台列表失败");
  return res.json();
}

export async function validatePlatformCredentials(data: {
  platform_type: string;
  appid?: string;
  secret_key?: string;
  api_token?: string;
  client_id?: string;
  client_secret?: string;
  domain?: string;
  project_id?: number;
}): Promise<{ valid: boolean; detail: string }> {
  const res = await apiFetch("/platforms/validate", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "凭据验证失败");
  return res.json();
}

export async function listPlatformBots(data: {
  platform_type: string;
  appid?: string;
  secret_key?: string;
  api_token?: string;
  client_id?: string;
  client_secret?: string;
  domain?: string;
  project_id?: number;
}): Promise<PlatformBotItem[]> {
  const res = await apiFetch("/platforms/bots", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "获取 Bot 列表失败");
  return res.json();
}

export async function importAgent(data: PlatformImportRequest): Promise<Agent> {
  const res = await apiFetch("/platforms/import", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "导入 Agent 失败");
  return res.json();
}
