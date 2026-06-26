"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { listAgents, createLink, listLinks, revokeLink, deleteAgent, type Agent, type ShareLink } from "@/lib/api";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState("");
  const [expireDays, setExpireDays] = useState(7);

  function load() {
    setLoading(true);
    Promise.all([
      listAgents().then((a) => setAgent(a.find((x) => x.id === id) || null)),
      listLinks(id).catch(() => []),
    ])
      .then(([, l]) => setLinks(l))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [id]);

  async function handleCreateLink() {
    setCreating(true);
    try {
      const link = await createLink(id, expireDays);
      setLinks((prev) => [link, ...prev]);
      showToast("链接已创建");
    } catch (e: unknown) {
      showToast("创建失败: " + (e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(linkId: string) {
    try {
      await revokeLink(linkId);
      setLinks((prev) => prev.map((l) => l.id === linkId ? { ...l, status: "revoked" } : l));
      showToast("链接已失效");
    } catch (e: unknown) {
      showToast("操作失败: " + (e as Error).message);
    }
  }

  async function handleDelete() {
    if (!confirm("确定要删除此 Agent？")) return;
    try {
      await deleteAgent(id);
      router.push("/agents");
    } catch (e: unknown) {
      showToast("删除失败: " + (e as Error).message);
    }
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  function copyToClipboard(url: string) {
    navigator.clipboard.writeText(url).then(() => showToast("已复制到剪贴板"));
  }

  if (loading) return <div className="loading-text">加载中...</div>;
  if (!agent) return <div className="error-text">Agent 不存在</div>;

  return (
    <>
      <div className="admin-page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={() => router.push("/agents")} className="admin-btn-link">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            返回
          </button>
          <h1>{agent.name}</h1>
          <span className={`badge ${agent.status === "active" ? "badge-success" : "badge-danger"}`}>
            {agent.status === "active" ? "在线" : "已停用"}
          </span>
        </div>
        <button onClick={handleDelete} className="admin-btn admin-btn-danger admin-btn-sm">
          删除
        </button>
      </div>

      <div className="admin-content">
        {/* Agent Info */}
        <div style={{ marginBottom: 32 }}>
          <div className="admin-card" style={{ marginBottom: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: "12px 0", fontSize: 13 }}>
              <span style={{ color: "#999" }}>API 地址</span>
              <code style={{ background: "#f5f5f5", padding: "2px 8px", borderRadius: 4, fontSize: 12 }}>
                {agent.api_endpoint || "未配置"}
              </code>
              <span style={{ color: "#999" }}>权限</span>
              <span>{agent.visibility === "public" ? "全员可用" : agent.visibility === "department" ? "按部门" : "指定用户"}</span>
              <span style={{ color: "#999" }}>创建时间</span>
              <span>{new Date(agent.created_at).toLocaleString("zh-CN")}</span>
            </div>
          </div>
        </div>

        {/* Share Links */}
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>分享链接</h2>

        <div className="admin-card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: 12, color: "#999", marginBottom: 4 }}>过期天数</label>
              <input
                type="number"
                value={expireDays}
                onChange={(e) => setExpireDays(Number(e.target.value))}
                min={1}
                max={365}
                className="admin-input"
                style={{ width: 100 }}
              />
            </div>
            <button onClick={handleCreateLink} className="admin-btn admin-btn-primary" disabled={creating}>
              {creating ? "创建中..." : "生成链接"}
            </button>
          </div>
        </div>

        {links.length === 0 && (
          <div className="empty-text">尚未创建分享链接</div>
        )}

        {links.map((link) => (
          <div key={link.id} className="link-item">
            <div>
              <code>{link.share_url}</code>
              <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                <span className={`badge ${link.status === "active" ? "badge-success" : "badge-danger"}`}>
                  {link.status === "active" ? "有效" : "已失效"}
                </span>
                {link.expire_at && (
                  <span style={{ fontSize: 11, color: "#999" }}>
                    过期: {new Date(link.expire_at).toLocaleDateString("zh-CN")}
                  </span>
                )}
                <span style={{ fontSize: 11, color: "#bbb" }}>
                  创建: {new Date(link.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              {link.status === "active" && (
                <>
                  <button onClick={() => copyToClipboard(link.share_url)} className="admin-btn admin-btn-secondary admin-btn-sm">
                    复制
                  </button>
                  <button onClick={() => handleRevoke(link.id)} className="admin-btn admin-btn-danger admin-btn-sm">
                    失效
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {toast && <div className="toast">{toast}</div>}
    </>
  );
}
