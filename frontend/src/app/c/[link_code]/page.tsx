"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isLoggedIn, getAgentByLink, createConversation, sendMessage as sendMsgViaLink } from "@/lib/api";
import ChatArea from "@/components/ChatArea";

export function generateStaticParams() {
  return [];
}

export default function ShareLinkChatPage() {
  const pathname = usePathname();
  const linkCode = pathname?.split("/c/")[1] || "";
  const router = useRouter();
  const [agentName, setAgentName] = useState("AI 助手");
  const [agentId, setAgentId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [convId, setConvId] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace(`/login`);
      return;
    }
    getAgentByLink(linkCode)
      .then((a) => {
        setAgentName(a.name);
        setAgentId(a.id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [linkCode, router]);

  // Create new conversation for this agent (resets context)
  const handleNewChat = useCallback(async () => {
    if (!agentId) return;
    try {
      const conv = await createConversation(agentId);
      setConvId(conv.id);
    } catch {
      setConvId(null);
    }
  }, [agentId]);

  if (loading) return <div className="loading-screen">加载中...</div>;

  return (
    <ChatArea
      mode={convId ? "conv" : "link"}
      agentName={agentName}
      linkCode={linkCode}
      convId={convId}
      onNewChatRequested={handleNewChat}
    />
  );
}
