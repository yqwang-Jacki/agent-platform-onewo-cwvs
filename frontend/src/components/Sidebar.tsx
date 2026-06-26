"use client";

import { useEffect, useState } from "react";
import {
  listAccessibleAgents,
  getConversations,
  createConversation,
  logout,
  getProfile,
  type AgentListItem,
  type ConversationSummary,
  type UserProfile,
} from "@/lib/api";

type SidebarProps = {
  activeAgentId: string | null;
  activeConvId: string | null;
  onSelectAgent: (agentId: string, convId: string | null) => void;
  onNewChat: () => void;
};

export default function Sidebar({ activeAgentId, activeConvId, onSelectAgent, onNewChat }: SidebarProps) {
  const [agents, setAgents] = useState<AgentListItem[]>([]);
  const [convs, setConvs] = useState<ConversationSummary[]>([]);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listAccessibleAgents().catch(() => []),
      getConversations().catch(() => []),
      getProfile().catch(() => null),
    ]).then(([a, c, p]) => {
      setAgents(a);
      setConvs(c);
      setProfile(p);
      if (a.length > 0 && !activeAgentId) {
        setExpandedAgent(a[0].id);
      }
    }).finally(() => setLoading(false));
  }, []);

  // Group conversations by agent
  const convsByAgent: Record<string, ConversationSummary[]> = {};
  convs.forEach((c) => {
    if (!convsByAgent[c.agent_id]) convsByAgent[c.agent_id] = [];
    convsByAgent[c.agent_id].push(c);
  });

  async function handleNewChatForAgent(agentId: string) {
    try {
      const conv = await createConversation(agentId);
      onSelectAgent(agentId, conv.id);
      // Refresh conversation list
      const fresh = await getConversations().catch(() => []);
      setConvs(fresh);
    } catch {
      onSelectAgent(agentId, null);
    }
  }

  function toggleExpand(agentId: string) {
    setExpandedAgent((prev) => (prev === agentId ? null : agentId));
  }

  return (
    <aside className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <button className="btn-new-chat" onClick={onNewChat}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          发起新对话
        </button>
      </div>

      {/* Agent list */}
      <div className="sidebar-content">
        {loading && (
          <div style={{ padding: "16px", color: "#999", fontSize: 13 }}>加载中...</div>
        )}

        {!loading && agents.length === 0 && (
          <div style={{ padding: "16px", color: "#999", fontSize: 13, textAlign: "center" }}>
            暂无可用 Agent
          </div>
        )}

        {agents.map((agent) => (
          <div key={agent.id}>
            <div
              className={`agent-item ${activeAgentId === agent.id ? "active" : ""}`}
              onClick={() => toggleExpand(agent.id)}
            >
              <div className="agent-avatar">
                {agent.name.charAt(0).toUpperCase()}
              </div>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {agent.name}
              </span>
              <svg
                width="14" height="14" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" strokeWidth="2"
                style={{
                  transform: expandedAgent === agent.id ? "rotate(90deg)" : "rotate(0deg)",
                  transition: "transform 0.15s",
                  flexShrink: 0,
                }}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>

            {/* Conversations under this agent */}
            {expandedAgent === agent.id && (
              <div>
                <div
                  className="conv-item"
                  onClick={() => handleNewChatForAgent(agent.id)}
                  style={{ color: "#999", fontStyle: "italic" }}
                >
                  + 新建会话
                </div>

                {(convsByAgent[agent.id] || []).map((conv) => (
                  <div
                    key={conv.id}
                    className={`conv-item ${activeConvId === conv.id ? "active" : ""}`}
                    onClick={() => onSelectAgent(agent.id, conv.id)}
                  >
                    <span
                      style={{
                        width: 6, height: 6, borderRadius: "50%",
                        background: activeConvId === conv.id ? "#111" : "transparent",
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {conv.last_message || "新会话"}
                    </span>
                  </div>
                ))}

                {(convsByAgent[agent.id] || []).length === 0 && (
                  <div className="conv-item" style={{ cursor: "default" }}>
                    <span style={{ fontSize: 11 }}>暂无会话</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer - Profile */}
      <div className="sidebar-footer">
        <div style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>
          {profile?.name || "用户"}
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <a
            href="/profile"
            style={{ fontSize: 12, color: "#666", textDecoration: "none" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#111")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#666")}
          >
            个人中心
          </a>
          <button
            onClick={() => logout()}
            style={{
              fontSize: 12, color: "#999", background: "none",
              border: "none", cursor: "pointer", padding: 0,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#999")}
          >
            退出
          </button>
        </div>
      </div>
    </aside>
  );
}
