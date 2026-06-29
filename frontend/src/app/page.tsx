"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn, getProfile, type UserProfile } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import ChatArea from "@/components/ChatArea";

export default function MainPage() {
  return (
    <Suspense fallback={<div className="loading-screen">加载中...</div>}>
      <MainPageInner />
    </Suspense>
  );
}

function MainPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [mounted, setMounted] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [linkCode, setLinkCode] = useState<string | null>(null);
  const [mode, setMode] = useState<"welcome" | "link" | "conv">("welcome");

  // Read URL params on mount (after Suspense resolves)
  useEffect(() => {
    setActiveAgentId(searchParams.get("agent") || null);
    setActiveConvId(searchParams.get("conv") || null);
    const link = searchParams.get("link");
    if (link) {
      setLinkCode(link);
      setMode("link");
    }
  }, []);

  // Skip pre-render issues - only init searchParams after mount
  useEffect(() => {
    setMounted(true);
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    getProfile()
      .then((p) => setProfile(p))
      .catch(() => router.replace("/login"))
      .finally(() => setAuthChecked(true));
  }, []);

  // Update URL params when navigation changes
  function updateUrl(agentId: string | null, convId: string | null) {
    const params = new URLSearchParams();
    if (agentId) params.set("agent", agentId);
    if (convId) params.set("conv", convId);
    const qs = params.toString();
    router.replace(qs ? `/?${qs}` : "/", { scroll: false });
  }

  const handleSelectAgent = useCallback(
    (agentId: string, convId: string | null) => {
      setActiveAgentId(agentId);
      setActiveConvId(convId);
      setLinkCode(null);
      setMode(convId ? "conv" : "welcome");
      updateUrl(agentId, convId);
    },
    [router]
  );

  const handleNewChat = useCallback(() => {
    setActiveAgentId(null);
    setActiveConvId(null);
    setLinkCode(null);
    setMode("welcome");
    router.replace("/", { scroll: false });
  }, [router]);

  // Handle share link flow (loaded via link param or separate page redirect)
  // Already handled in the mount useEffect above

  if (!mounted || !authChecked) {
    return <div className="loading-screen">加载中...</div>;
  }

  return (
    <div style={{ display: "flex", width: "100%", height: "100vh" }}>
      {/* Mobile menu button */}
      <button
        className="mobile-menu-btn"
        onClick={() => {
          const sidebar = document.querySelector(".sidebar");
          sidebar?.classList.toggle("open");
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <Sidebar
        activeAgentId={activeAgentId}
        activeConvId={activeConvId}
        onSelectAgent={handleSelectAgent}
        onNewChat={handleNewChat}
      />

      <ChatArea
        mode={mode}
        agentName={profile?.name ? undefined : undefined}
        linkCode={linkCode || undefined}
        convId={activeConvId}
        onNewChatRequested={handleNewChat}
      />
    </div>
  );
}
