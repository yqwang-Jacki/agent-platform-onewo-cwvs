"use client";

import { useState, useEffect, useRef } from "react";
import {
  getConversation,
  getAgentByLink,
  sendMessage as sendMsgViaLink,
  type ConversationResponse,
  type AgentPublicInfo,
  type Message,
} from "@/lib/api";

type ChatAreaProps = {
  mode: "welcome" | "link" | "conv";
  agentName?: string;
  linkCode?: string;
  convId?: string | null;
  onNewChatRequested: () => void;
};

export default function ChatArea({
  mode,
  agentName,
  linkCode,
  convId,
  onNewChatRequested,
}: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [convLoading, setConvLoading] = useState(false);
  const [headerName, setHeaderName] = useState(agentName || "AI 助手");
  const [showWelcome, setShowWelcome] = useState(mode === "welcome");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load conversation messages
  useEffect(() => {
    if (mode === "conv" && convId) {
      setConvLoading(true);
      getConversation(convId)
        .then((conv) => {
          setMessages(conv.messages);
          setHeaderName(conv.agent_name || agentName || "AI 助手");
          setShowWelcome(false);
        })
        .catch(() => {
          setMessages([]);
          setShowWelcome(true);
        })
        .finally(() => setConvLoading(false));
    } else if (mode === "link" && linkCode) {
      getAgentByLink(linkCode)
        .then((a) => {
          setHeaderName(a.name);
          setShowWelcome(true);
          setMessages([]);
        })
        .catch(() => setHeaderName("AI 助手"));
    } else if (mode === "welcome") {
      setMessages([]);
      setShowWelcome(true);
      setHeaderName("AI 助手");
    }
  }, [mode, convId, linkCode, agentName]);

  // Auto-resize textarea
  function adjustHeight() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "24px";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const content = input.trim();
    if (!content || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      tokens_used: 0,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setShowWelcome(false);
    setLoading(true);

    try {
      let reply: Message;

      if (mode === "conv" && convId) {
        const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const token = localStorage.getItem("access_token");
        const res = await fetch(`${BASE}/chat/conversations/${convId}/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content, stream: false }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || "发送失败");
        reply = await res.json();
      } else if (mode === "link" && linkCode) {
        reply = await sendMsgViaLink(linkCode, content);
      } else {
        throw new Error("无发获取会话");
      }

      setMessages((prev) => [...prev, reply]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: "抱歉，发送失败：" + (e as Error).message,
          tokens_used: 0,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  }

  return (
    <div className="chat-main">
      {/* Header */}
      <header
        style={{
          padding: "14px 24px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#fff",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            className="agent-avatar"
            style={{ width: 32, height: 32, fontSize: 14 }}
          >
            {headerName.charAt(0).toUpperCase()}
          </div>
          <span style={{ fontSize: 15, fontWeight: 600 }}>{headerName}</span>
        </div>
        <button
          onClick={onNewChatRequested}
          style={{
            background: "none",
            border: "1px solid #e5e5e5",
            borderRadius: 6,
            padding: "6px 12px",
            fontSize: 12,
            color: "#666",
            cursor: "pointer",
          }}
        >
          新建对话
        </button>
      </header>

      {/* Content */}
      {convLoading && (
        <div className="loading-screen">加载会话...</div>
      )}

      {!convLoading && showWelcome && (
        <div className="welcome-screen">
          <div className="welcome-logo">{headerName}</div>
          <p style={{ color: "#999", fontSize: 14 }}>
            {mode === "welcome"
              ? "选择一个 Agent 开始对话"
              : "发送消息开始对话"}
          </p>
        </div>
      )}

      {!convLoading && !showWelcome && (
        <div className="messages-container">
          {messages.map((m, i) => (
            <div key={m.id || i} className={`message-row ${m.role}`}>
              <div className="message-inner">
                <div className={`message-avatar ${m.role}`}>
                  {m.role === "user" ? "U" : headerName.charAt(0)}
                </div>
                <div className="message-body">
                  {m.content.split("\n").map((line, j) => (
                    <p key={j}>{line || "\u00A0"}</p>
                  ))}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="message-row assistant">
              <div className="message-inner">
                <div className="message-avatar assistant" style={{ opacity: 0.5 }}>
                  {headerName.charAt(0)}
                </div>
                <div className="message-body" style={{ color: "#999" }}>
                  <p>思考中...</p>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div className="chat-input-wrapper">
        <form onSubmit={handleSend}>
          <div className="chat-input-box">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                adjustHeight();
              }}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === "welcome"
                  ? "选择一个 Agent 开始对话..."
                  : `向 ${headerName} 发送消息...`
              }
              rows={1}
              disabled={mode === "welcome"}
            />
            <button
              type="submit"
              className="send-btn"
              disabled={!input.trim() || loading || mode === "welcome"}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
        </form>
        <p style={{ fontSize: 11, color: "#bbb", textAlign: "center", marginTop: 8 }}>
          {headerName} 可能会犯错，请核实重要信息
        </p>
      </div>
    </div>
  );
}
