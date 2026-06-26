"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  listPlatforms,
  validatePlatformCredentials,
  listPlatformBots,
  importAgent,
  type PlatformInfo,
  type PlatformBotItem,
} from "@/lib/api";

// 模拟部门列表
const DEPARTMENTS = ["技术部", "产品部", "市场部", "销售部", "AI平台组", "业务部", "财务部", "人力资源部"];

type Step = "select-platform" | "credentials" | "select-bot" | "configure";

export default function PlatformImportDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("select-platform");
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformInfo | null>(null);

  // Credentials
  const [appid, setAppid] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [domain, setDomain] = useState("");
  const [projectId, setProjectId] = useState("");

  // Bot list
  const [bots, setBots] = useState<PlatformBotItem[]>([]);
  const [selectedBot, setSelectedBot] = useState<PlatformBotItem | null>(null);
  const [customBotId, setCustomBotId] = useState("");
  const [customBotName, setCustomBotName] = useState("");

  // Config
  const [agentName, setAgentName] = useState("");
  const [visibility, setVisibility] = useState<"public" | "department" | "specific">("public");
  const [selectedDepts, setSelectedDepts] = useState<string[]>([]);

  // State
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    listPlatforms()
      .then((p) => setPlatforms(p.filter((pl) => pl.platform_type !== "custom")))
      .catch(() => setErr("获取平台列表失败"));
  }, []);

  function selectPlatform(p: PlatformInfo) {
    setSelectedPlatform(p);
    setStep("credentials");
    setErr("");
    // Reset credentials based on platform
    setAppid("");
    setSecretKey("");
    setApiToken("");
    setDomain("");
    setProjectId("");
  }

  async function validateAndFetch() {
    setErr("");
    setLoading(true);
    try {
      const data: Record<string, unknown> = {
        platform_type: selectedPlatform!.platform_type,
      };
      if (selectedPlatform!.platform_type === "gc") {
        data.appid = appid;
        data.secret_key = secretKey;
      } else if (selectedPlatform!.platform_type === "coze") {
        data.api_token = apiToken;
        data.domain = domain;
        data.project_id = parseInt(projectId) || 0;
      }

      const result = await validatePlatformCredentials(data as any);
      if (!result.valid) {
        setErr("凭据验证失败，请检查后重试");
        setLoading(false);
        return;
      }

      const botList = await listPlatformBots(data as any);
      setBots(botList);
      setStep("select-bot");
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function selectBotOrCustom() {
    setAgentName(selectedBot?.name || customBotName);
    setStep("configure");
  }

  async function doImport() {
    setErr("");
    setLoading(true);
    try {
      let perm: Record<string, unknown> | null = null;
      if (visibility === "department") {
        if (selectedDepts.length === 0) { setErr("请至少选择一个部门"); setLoading(false); return; }
        perm = { departments: selectedDepts };
      }

      await importAgent({
        platform_type: selectedPlatform!.platform_type,
        appid,
        secret_key: secretKey,
        api_token: apiToken,
        domain,
        project_id: parseInt(projectId) || 0,
        bot_id: selectedBot?.bot_id || customBotId,
        bot_name: selectedBot?.name || customBotName,
        name: agentName,
        visibility,
        permission_config: perm,
      });
      router.refresh();
      onClose();
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function PlatformIcon({ icon }: { icon: string }) {
    return <span style={{ fontSize: 36, marginBottom: 12, display: "block" }}>{icon}</span>;
  }

  return (
    <>
      {/* Overlay */}
      <div
        style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 999,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
        onClick={onClose}
      >
        {/* Dialog */}
        <div
          className="admin-card"
          style={{
            width: 560, maxWidth: "92vw", maxHeight: "85vh", overflowY: "auto",
            padding: 28, position: "relative",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close */}
          <button
            onClick={onClose}
            style={{ position: "absolute", top: 16, right: 16, background: "none", border: "none", cursor: "pointer", color: "#666", fontSize: 20 }}
          >
            ✕
          </button>

          {/* Step indicator */}
          <div style={{ display: "flex", gap: 8, marginBottom: 24, justifyContent: "center" }}>
            {["选择平台", "输入凭据", "发现 Bot", "配置发布"].map((label, i) => {
              const stepIdx = ["select-platform", "credentials", "select-bot", "configure"].indexOf(step);
              const isActive = stepIdx === i;
              const isDone = stepIdx > i;
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span
                    style={{
                      display: "inline-flex", alignItems: "center", justifyContent: "center",
                      width: 22, height: 22, borderRadius: "50%", fontSize: 11, fontWeight: 600,
                      background: isActive ? "#3b82f6" : isDone ? "#10b981" : "#e5e7eb",
                      color: isActive || isDone ? "#fff" : "#666",
                    }}
                  >
                    {isDone ? "✓" : i + 1}
                  </span>
                  <span style={{ fontSize: 11, color: isActive ? "#3b82f6" : isDone ? "#10b981" : "#999" }}>
                    {label}
                  </span>
                  {i < 3 && <span style={{ color: "#ddd", margin: "0 2px" }}>→</span>}
                </div>
              );
            })}
          </div>

          {/* Step 1: Select Platform */}
          {step === "select-platform" && (
            <>
              <h2 style={{ fontSize: 18, marginBottom: 8 }}>选择 Agent 平台</h2>
              <p style={{ color: "#666", fontSize: 13, marginBottom: 20 }}>
                从支持的平台一键导入 Agent，无需手动配置 API 地址
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {platforms.map((p) => (
                  <button
                    key={p.platform_type}
                    onClick={() => selectPlatform(p)}
                    className="admin-card"
                    style={{ display: "flex", alignItems: "center", gap: 16, padding: 16, textAlign: "left", border: "1px solid #e5e7eb", cursor: "pointer", background: "white" }}
                  >
                    <span style={{ fontSize: 32 }}>{p.icon}</span>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 15 }}>{p.label}</div>
                      <div style={{ color: "#888", fontSize: 12, marginTop: 2 }}>{p.help_text}</div>
                    </div>
                    <svg style={{ marginLeft: "auto", width: 16, height: 16, color: "#bbb" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Step 2: Credentials */}
          {step === "credentials" && selectedPlatform && (
            <>
              <button onClick={() => setStep("select-platform")} className="admin-btn-link" style={{ marginBottom: 12 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
                返回选择平台
              </button>
              <h2 style={{ fontSize: 18, marginBottom: 8 }}>
                {selectedPlatform.icon} {selectedPlatform.label} — 输入凭据
              </h2>
              <p style={{ color: "#666", fontSize: 13, marginBottom: 16 }}>{selectedPlatform.help_text}</p>

              {selectedPlatform.platform_type === "gc" && (
                <>
                  <div className="admin-form-group">
                    <label>AppID</label>
                    <input className="admin-input" value={appid} onChange={(e) => setAppid(e.target.value)} placeholder="GC 平台 AppID" />
                  </div>
                  <div className="admin-form-group">
                    <label>SecretKey</label>
                    <input className="admin-input" type="password" value={secretKey} onChange={(e) => setSecretKey(e.target.value)} placeholder="GC 平台 SecretKey" />
                  </div>
                </>
              )}

              {selectedPlatform.platform_type === "coze" && (
                <>
                  <div className="admin-form-group">
                    <label>API Token</label>
                    <textarea
                      className="admin-textarea"
                      value={apiToken}
                      onChange={(e) => setApiToken(e.target.value)}
                      placeholder="Coze 平台创建的 API Token (JWT 格式)"
                      rows={3}
                    />
                  </div>
                  <div className="admin-form-group">
                    <label>部署域名</label>
                    <input className="admin-input" value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="例如: 6dzhzw2vvm.coze.site" />
                  </div>
                  <div className="admin-form-group">
                    <label>Project ID</label>
                    <input className="admin-input" type="number" value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="Coze 项目 ID" />
                  </div>
                </>
              )}

              {err && <p className="error-text">{err}</p>}

              <button
                onClick={validateAndFetch}
                className="admin-btn admin-btn-primary"
                disabled={loading}
                style={{ marginTop: 8 }}
              >
                {loading ? "验证中..." : "验证并获取 Bot 列表"}
              </button>
            </>
          )}

          {/* Step 3: Select Bot */}
          {step === "select-bot" && (
            <>
              <button onClick={() => setStep("credentials")} className="admin-btn-link" style={{ marginBottom: 12 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
                返回修改凭据
              </button>
              <h2 style={{ fontSize: 18, marginBottom: 8 }}>选择要导入的 Bot</h2>
              <p style={{ color: "#666", fontSize: 13, marginBottom: 16 }}>
                选择平台上的 AI Bot，或手动输入 Bot 信息
              </p>

              {bots.length > 0 && bots[0].bot_id !== "" ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
                  {bots.map((bot) => (
                    <button
                      key={bot.bot_id}
                      onClick={() => { setSelectedBot(bot); setCustomBotId(bot.bot_id); setCustomBotName(bot.name); }}
                      className="admin-card"
                      style={{
                        display: "flex", alignItems: "center", gap: 12, padding: 12,
                        textAlign: "left", cursor: "pointer",
                        border: selectedBot?.bot_id === bot.bot_id ? "2px solid #3b82f6" : "1px solid #e5e7eb",
                        background: selectedBot?.bot_id === bot.bot_id ? "#eff6ff" : "white",
                      }}
                    >
                      <span style={{ fontSize: 24 }}>🤖</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{bot.name}</div>
                        {bot.description && <div style={{ color: "#888", fontSize: 12 }}>{bot.description}</div>}
                      </div>
                      {selectedBot?.bot_id === bot.bot_id && (
                        <span style={{ color: "#3b82f6", fontSize: 20 }}>✓</span>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div style={{ padding: 12, background: "#fefce8", borderRadius: 8, marginBottom: 16, fontSize: 13, color: "#92400e" }}>
                  自动获取失败，请手动输入 Bot 信息
                </div>
              )}

              <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>手动输入 Bot 信息</div>
                <div className="admin-form-group">
                  <label>Bot ID</label>
                  <input className="admin-input" value={customBotId} onChange={(e) => setCustomBotId(e.target.value)} placeholder="平台上的 Bot ID" />
                </div>
                <div className="admin-form-group">
                  <label>Bot 名称</label>
                  <input className="admin-input" value={customBotName} onChange={(e) => setCustomBotName(e.target.value)} placeholder="给 Bot 取个名字" />
                </div>
              </div>

              <button
                onClick={selectBotOrCustom}
                className="admin-btn admin-btn-primary"
                disabled={!customBotId && !customBotName}
              >
                下一步：配置发布
              </button>
            </>
          )}

          {/* Step 4: Configure & Publish */}
          {step === "configure" && (
            <>
              <button onClick={() => setStep("select-bot")} className="admin-btn-link" style={{ marginBottom: 12 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
                返回选择 Bot
              </button>
              <h2 style={{ fontSize: 18, marginBottom: 8 }}>配置并发布</h2>

              <div className="admin-form-group">
                <label>Agent 名称 *</label>
                <input className="admin-input" value={agentName} onChange={(e) => setAgentName(e.target.value)} placeholder="在平台上显示的名称" />
              </div>

              <div className="admin-form-group">
                <label>可见性</label>
                <select className="admin-select" value={visibility} onChange={(e) => setVisibility(e.target.value as any)}>
                  <option value="public">全员可见</option>
                  <option value="department">按部门</option>
                </select>
              </div>

              {visibility === "department" && (
                <div className="admin-form-group">
                  <label>选择可见部门 *</label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                    {DEPARTMENTS.map((dept) => (
                      <button
                        key={dept} type="button"
                        className={`perm-chip${selectedDepts.includes(dept) ? " selected" : ""}`}
                        onClick={() => setSelectedDepts((prev) =>
                          prev.includes(dept) ? prev.filter((d) => d !== dept) : [...prev, dept]
                        )}
                      >
                        {selectedDepts.includes(dept) && (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                        )}
                        {dept}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Summary */}
              <div style={{ padding: 12, background: "#f3f4f6", borderRadius: 8, fontSize: 12, marginTop: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>导入摘要</div>
                <div>平台: {selectedPlatform?.label}</div>
                <div>Bot: {selectedBot?.name || customBotName} ({selectedBot?.bot_id || customBotId})</div>
                <div>Agent 名称: {agentName}</div>
                <div>可见性: {visibility === "public" ? "全员可见" : `按部门(${selectedDepts.length}个)`}</div>
              </div>

              {err && <p className="error-text">{err}</p>}

              <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
                <button onClick={doImport} className="admin-btn admin-btn-primary" disabled={loading || !agentName}>
                  {loading ? "导入中..." : "一键发布"}
                </button>
                <button onClick={onClose} className="admin-btn admin-btn-secondary">取消</button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
