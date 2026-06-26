"use client";

import { useEffect, useState } from "react";
import { getConversations, logout } from "@/lib/api";
import type { ConversationSummary } from "@/lib/api";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    getConversations()
      .then((data) => setConversations(data))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "40px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600 }}>我的会话</h1>
        <button
          onClick={() => logout()}
          style={{ padding: "8px 16px", fontSize: 14, color: "#3b82f6", background: "transparent", border: "1px solid #3b82f6", borderRadius: 6, cursor: "pointer" }}
        >
          退出登录
        </button>
      </div>

      {loading && <p style={{ color: "#666" }}>加载中...</p>}
      {err && <p style={{ color: "#ef4444" }}>{err}</p>}

      {!loading && !err && conversations.length === 0 && (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#666" }}>
          <p>暂无会话</p>
          <p style={{ fontSize: 14, marginTop: 8 }}>打开任意 Agent 分享链接即可开始对话</p>
        </div>
      )}

      <div style={{ display: "grid", gap: 12 }}>
        {conversations.map((conv) => (
          <div
            key={conv.id}
            style={{ padding: 16, border: "1px solid #e5e5e5", borderRadius: 8, textDecoration: "none", color: "inherit" }}
          >
            <p style={{ fontSize: 14, color: "#333" }}>会话 ID: {conv.id}</p>
            <p style={{ fontSize: 13, color: "#666", marginTop: 4 }}>Agent: {conv.agent_id}</p>
            <p style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
              {conv.message_count} 条消息 · 最后活跃: {new Date(conv.last_active_at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </main>
  );
}
