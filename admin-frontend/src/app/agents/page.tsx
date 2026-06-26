"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listAgents, type Agent } from "@/lib/api";
import PlatformImportDialog from "@/components/PlatformImportDialog";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [showImport, setShowImport] = useState(false);

  function load() {
    setLoading(true);
    listAgents()
      .then(setAgents)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  const visibilityLabel: Record<string, { cls: string; text: string }> = {
    public: { cls: "badge-info", text: "全员" },
    department: { cls: "badge-warning", text: "按部门" },
    specific: { cls: "badge-purple", text: "指定用户" },
  };

  const platformLabel: Record<string, string> = {
    custom: "自定义",
    gc: "GC平台",
    coze: "Coze",
  };

  return (
    <>
      {showImport && <PlatformImportDialog onClose={() => { setShowImport(false); load(); }} />}

      <div className="admin-page-header">
        <h1>Agent 管理</h1>
        <button onClick={() => setShowImport(true)} className="admin-btn admin-btn-primary">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          发布 Agent
        </button>
      </div>

      <div className="admin-content">
        {loading && <div className="loading-text">加载中...</div>}
        {err && <div className="error-text">{err}</div>}

        {!loading && !err && agents.length === 0 && (
          <div className="empty-text">
            还没有 Agent，点击右上角「发布 Agent」开始
          </div>
        )}

        <div className="agent-grid">
          {agents.map((agent) => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}`}
              className="admin-card"
              style={{ textDecoration: "none", display: "block" }}
            >
              <div className="agent-card-header">
                <h3>{agent.name}</h3>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {(agent as any).platform_type && (agent as any).platform_type !== "custom" && (
                    <span className="badge" style={{ background: "#ede9fe", color: "#7c3aed", fontSize: 11 }}>
                      {platformLabel[(agent as any).platform_type] || (agent as any).platform_type}
                    </span>
                  )}
                  <span className={`badge ${agent.status === "active" ? "badge-success" : "badge-danger"}`}>
                    {agent.status === "active" ? "在线" : "已停用"}
                  </span>
                </div>
              </div>

              <div className="agent-card-meta">
                <span>
                  权限：
                  <span className={`badge ${visibilityLabel[agent.visibility]?.cls || "badge-info"}`}>
                    {visibilityLabel[agent.visibility]?.text || agent.visibility}
                  </span>
                </span>
                <span style={{ color: "#999", wordBreak: "break-all" }}>{agent.api_endpoint}</span>
                <span style={{ fontSize: 11, marginTop: 4 }}>
                  创建于 {new Date(agent.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
