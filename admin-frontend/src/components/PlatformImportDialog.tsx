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

/* ── SVG 图标 ── */

function IconGC({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="8" fill="#111" />
      <path d="M8 12h16M8 16h12M8 20h8" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function IconCoze({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="8" fill="#fff" stroke="#e5e5e5" strokeWidth="1" />
      <circle cx="11" cy="14" r="3" stroke="#333" strokeWidth="1.5" />
      <circle cx="21" cy="14" r="3" stroke="#333" strokeWidth="1.5" />
      <path d="M9 22c0-2.2 2.7-4 6-4h2c3.3 0 6 1.8 6 4" stroke="#333" strokeWidth="1.5" strokeLinecap="round" />
      {/* antenna */}
      <line x1="11" y1="9" x2="10" y2="6" stroke="#333" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="21" y1="9" x2="22" y2="6" stroke="#333" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function ChevronRight({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function ChevronLeft({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function CloseIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function CheckIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function BotPlaceholder({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <rect width="28" height="28" rx="6" fill="#f5f5f5" />
      <circle cx="10" cy="13" r="2.5" stroke="#999" strokeWidth="1.2" />
      <circle cx="18" cy="13" r="2.5" stroke="#999" strokeWidth="1.2" />
      <path d="M9 19c0-1.7 2.2-3 5-3s5 1.3 5 3" stroke="#999" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

/* ── 图标映射 ── */

function PlatformIcon({ icon, size = 36 }: { icon: string; size?: number }) {
  if (icon === "gc") return <IconGC size={size} />;
  if (icon === "coze") return <IconCoze size={size} />;
  return null;
}

/* ── 主组件 ── */

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
    setAppid(""); setSecretKey(""); setApiToken(""); setDomain(""); setProjectId("");
  }

  async function validateAndFetch() {
    setErr("");
    setLoading(true);
    try {
      const data: Record<string, unknown> = { platform_type: selectedPlatform!.platform_type };
      if (selectedPlatform!.platform_type === "gc") {
        data.appid = appid; data.secret_key = secretKey;
      } else if (selectedPlatform!.platform_type === "coze") {
        data.api_token = apiToken;
        data.domain = domain;
        data.project_id = parseInt(projectId) || 0;
      }

      const result = await validatePlatformCredentials(data as any);
      if (!result.valid) {
        // 后端返回的 detail 字段包含具体错误码/消息
        const detail = (result as any).detail || "";
        setErr(detail || "凭据验证失败，请检查 API Token 和域名后重试");
        setLoading(false);
        return;
      }
      const botList = await listPlatformBots(data as any);
      setBots(botList);
      setStep("select-bot");
    } catch (e: unknown) {
      const msg = (e as Error).message || String(e);
      // 尝试提取 HTTP 状态码
      const codeMatch = msg.match(/\b(40[0-9]|4\d{2}|5\d{2})\b/);
      const code = codeMatch ? ` (${codeMatch[1]})` : "";
      setErr(`验证请求失败${code}: ${msg}`);
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
        appid, secret_key: secretKey, api_token: apiToken,
        domain, project_id: parseInt(projectId) || 0,
        bot_id: selectedBot?.bot_id || customBotId,
        bot_name: selectedBot?.name || customBotName,
        name: agentName, visibility, permission_config: perm,
      });
      router.refresh();
      onClose();
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  /* ── 步骤条 ── */
  const STEPS = [
    { key: "select-platform", label: "选择平台" },
    { key: "credentials", label: "输入凭据" },
    { key: "select-bot", label: "发现 Bot" },
    { key: "configure", label: "配置发布" },
  ] as const;

  return (
    <>
      {/* Overlay */}
      <div className="pi-overlay" onClick={onClose}>
        {/* Dialog */}
        <div className="pi-dialog" onClick={(e) => e.stopPropagation()}>
          {/* Header */}
          <div className="pi-header">
            <div className="pi-steps">
              {STEPS.map(({ key, label }, i) => {
                const currentIdx = STEPS.findIndex(s => s.key === step);
                const isActive = currentIdx === i;
                const isDone = currentIdx > i;
                return (
                  <div key={key} className={`pi-step ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}>
                    <span className="pi-step-num">{isDone ? <CheckIcon size={10} /> : i + 1}</span>
                    <span className="pi-step-label">{label}</span>
                    {i < STEPS.length - 1 && <span className="pi-step-line" />}
                  </div>
                );
              })}
            </div>
            <button className="pi-close" onClick={onClose}><CloseIcon /></button>
          </div>

          {/* Body */}
          <div className="pi-body">

            {/* ═══ Step 1: 选择平台 ═══ */}
            {step === "select-platform" && (
              <div className="pi-section">
                <div className="pi-section-title">选择 Agent 平台</div>
                <div className="pi-section-desc">从支持的平台一键导入 Agent，无需手动配置 API 地址</div>

                <div className="pi-platform-list">
                  {platforms.map((p) => (
                    <button
                      key={p.platform_type}
                      className="pi-platform-card"
                      onClick={() => selectPlatform(p)}
                    >
                      <div className="pi-platform-icon"><PlatformIcon icon={p.icon} /></div>
                      <div className="pi-platform-info">
                        <div className="pi-platform-name">{p.label}</div>
                        <div className="pi-platform-desc">{p.help_text}</div>
                      </div>
                      <div className="pi-platform-arrow"><ChevronRight /></div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ═══ Step 2: 输入凭据 ═══ */}
            {step === "credentials" && selectedPlatform && (
              <div className="pi-section">
                <button className="pi-back-btn" onClick={() => setStep("select-platform")}>
                  <ChevronLeft /> 返回选择平台
                </button>

                <div className="pi-section-title">
                  <span className="pi-title-icon"><PlatformIcon icon={selectedPlatform.icon} size={20} /></span>
                  {selectedPlatform.label} — 输入凭据
                </div>
                <div className="pi-section-desc">{selectedPlatform.help_text}</div>

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
                      <textarea className="admin-textarea" value={apiToken} onChange={(e) => setApiToken(e.target.value)} placeholder="Coze 平台创建的 API Token (cztei_xxx 格式)" rows={3} />
                    </div>
                    <div className="admin-form-group">
                      <label>部署域名</label>
                      <input className="admin-input" value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="例如: api.coze.cn 或 xxx.coze.site" />
                    </div>
                    <div className="admin-form-group">
                      <label>Project ID</label>
                      <input className="admin-input" type="number" value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="Coze 项目 ID (可选)" />
                    </div>
                  </>
                )}

                {err && <p className="error-text pi-error">{err}</p>}

                <button onClick={validateAndFetch} className="admin-btn admin-btn-primary pi-action-btn" disabled={loading}>
                  {loading ? "验证中..." : "验证并获取 Bot 列表"}
                </button>
              </div>
            )}

            {/* ═══ Step 3: 选择 Bot ═══ */}
            {step === "select-bot" && (
              <div className="pi-section">
                <button className="pi-back-btn" onClick={() => setStep("credentials")}><ChevronLeft /> 返回修改凭据</button>

                <div className="pi-section-title">选择要导入的 Bot</div>
                <div className="pi-section-desc">选择平台上的 AI Bot，或手动输入 Bot 信息</div>

                {bots.length > 0 && bots[0].bot_id !== "" ? (
                  <div className="pi-bot-list">
                    {bots.map((bot) => (
                      <button
                        key={bot.bot_id}
                        onClick={() => { setSelectedBot(bot); setCustomBotId(bot.bot_id); setCustomBotName(bot.name); }}
                        className={`pi-bot-card${selectedBot?.bot_id === bot.bot_id ? " selected" : ""}`}
                      >
                        <BotPlaceholder />
                        <div className="pi-bot-info">
                          <div className="pi-bot-name">{bot.name}</div>
                          {bot.description && <div className="pi-bot-desc">{bot.description}</div>}
                        </div>
                        {selectedBot?.bot_id === bot.bot_id && <div className="pi-bot-check"><CheckIcon size={16} /></div>}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="pi-warning">自动获取失败，请手动输入 Bot 信息</div>
                )}

                <div className="pi-manual-box">
                  <div className="pi-manual-label">手动输入 Bot 信息</div>
                  <div className="admin-form-group" style={{ marginBottom: 12 }}>
                    <label>Bot ID</label>
                    <input className="admin-input" value={customBotId} onChange={(e) => setCustomBotId(e.target.value)} placeholder="平台上的 Bot ID" />
                  </div>
                  <div className="admin-form-group" style={{ marginBottom: 0 }}>
                    <label>Bot 名称</label>
                    <input className="admin-input" value={customBotName} onChange={(e) => setCustomBotName(e.target.value)} placeholder="给 Bot 取个名字" />
                  </div>
                </div>

                <button onClick={selectBotOrCustom} className="admin-btn admin-btn-primary pi-action-btn" disabled={!customBotId && !customBotName}>
                  下一步：配置发布
                </button>
              </div>
            )}

            {/* ═══ Step 4: 配置发布 ═══ */}
            {step === "configure" && (
              <div className="pi-section">
                <button className="pi-back-btn" onClick={() => setStep("select-bot")}><ChevronLeft /> 返回选择 Bot</button>

                <div className="pi-section-title">配置并发布</div>

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
                        <button key={dept} type="button"
                          className={`perm-chip${selectedDepts.includes(dept) ? " selected" : ""}`}
                          onClick={() => setSelectedDepts(prev =>
                            prev.includes(dept) ? prev.filter(d => d !== dept) : [...prev, dept]
                          )}
                        >
                          {selectedDepts.includes(dept) && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>}
                          {dept}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pi-summary">
                  <div className="pi-summary-title">导入摘要</div>
                  <div className="pi-summary-row"><span className="pi-summary-k">平台</span><span>{selectedPlatform?.label}</span></div>
                  <div className="pi-summary-row"><span className="pi-summary-k">Bot</span><span>{selectedBot?.name || customBotName} ({selectedBot?.bot_id || customBotId})</span></div>
                  <div className="pi-summary-row"><span className="pi-summary-k">Agent 名称</span><span>{agentName}</span></div>
                  <div className="pi-summary-row"><span className="pi-summary-k">可见性</span><span>{visibility === "public" ? "全员可见" : `按部门(${selectedDepts.length}个)`}</span></div>
                </div>

                {err && <p className="error-text pi-error">{err}</p>}

                <div style={{ display: "flex", gap: 10 }}>
                  <button onClick={doImport} className="admin-btn admin-btn-primary" disabled={loading || !agentName}>
                    {loading ? "导入中..." : "发布"}
                  </button>
                  <button onClick={onClose} className="admin-btn admin-btn-secondary">取消</button>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </>
  );
}
