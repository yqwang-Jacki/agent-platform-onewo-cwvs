"use client";

import { useEffect, useState } from "react";
import { getTokenStats, type TokenStat } from "@/lib/api";

export default function UsagePage() {
  const [stats, setStats] = useState<TokenStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    getTokenStats()
      .then(setStats)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  const totalTokens = stats.reduce((s, x) => s + x.total_tokens, 0);
  const totalReqs = stats.reduce((s, x) => s + x.total_requests, 0);

  return (
    <>
      <div className="admin-page-header">
        <h1>用量统计</h1>
      </div>

      <div className="admin-content">
        {loading && <div className="loading-text">加载中...</div>}
        {err && <div className="error-text">{err}</div>}

        {!loading && !err && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
              <div className="admin-card">
                <div style={{ fontSize: 12, color: "#999", marginBottom: 8 }}>总 Token 消耗</div>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{totalTokens.toLocaleString()}</div>
              </div>
              <div className="admin-card">
                <div style={{ fontSize: 12, color: "#999", marginBottom: 8 }}>总请求数</div>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{totalReqs.toLocaleString()}</div>
              </div>
              <div className="admin-card">
                <div style={{ fontSize: 12, color: "#999", marginBottom: 8 }}>Agent 数量</div>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{stats.length}</div>
              </div>
            </div>

            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>按 Agent 统计</h2>

            {stats.length === 0 && (
              <div className="empty-text">暂无用量数据</div>
            )}

            <div style={{ display: "grid", gap: 8 }}>
              {stats.map((s) => (
                <div key={s.agent_id} className="admin-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>Agent {s.agent_id.slice(0, 8)}...</div>
                    <div style={{ fontSize: 12, color: "#999", marginTop: 2 }}>
                      {s.total_requests.toLocaleString()} 次请求
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 18, fontWeight: 700 }}>{s.total_tokens.toLocaleString()}</div>
                    <div style={{ fontSize: 11, color: "#999" }}>tokens</div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}
