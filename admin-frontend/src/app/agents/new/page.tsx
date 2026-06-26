"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createAgent, listAdminUsers, listRoles, type AdminUser } from "@/lib/api";

// 模拟部门列表（实际可从接口获取）
const DEPARTMENTS = ["技术部", "产品部", "市场部", "销售部", "AI平台组", "业务部", "财务部", "人力资源部"];

export default function CreateAgentPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    api_endpoint: "http://localhost:9999",
    api_headers: "{}",
    visibility: "public" as "public" | "department" | "specific",
  });
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedDepts, setSelectedDepts] = useState<string[]>([]);
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    listAdminUsers({}).then(setUsers).catch(() => {});
  }, []);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function toggleDept(dept: string) {
    setSelectedDepts((prev) =>
      prev.includes(dept) ? prev.filter((d) => d !== dept) : [...prev, dept]
    );
  }

  function toggleUser(uid: string) {
    setSelectedUserIds((prev) =>
      prev.includes(uid) ? prev.filter((u) => u !== uid) : [...prev, uid]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (!form.name || !form.api_endpoint) return setErr("名称和 API 地址为必填项");

    let headers = {};
    try { headers = JSON.parse(form.api_headers); } catch { return setErr("API Headers JSON 格式错误"); }

    let perm = {};
    if (form.visibility === "department") {
      if (selectedDepts.length === 0) return setErr("请至少选择一个部门");
      perm = { departments: selectedDepts };
    } else if (form.visibility === "specific") {
      if (selectedUserIds.length === 0) return setErr("请至少选择一个用户");
      perm = { user_ids: selectedUserIds };
    }

    setLoading(true);
    try {
      await createAgent({
        name: form.name,
        api_endpoint: form.api_endpoint,
        api_headers: headers,
        visibility: form.visibility,
        permission_config: perm,
        config: {},
      });
      router.push("/agents");
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

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
          <h1>发布 Agent</h1>
        </div>
      </div>

      <div className="admin-content">
        <div className="admin-card" style={{ maxWidth: 720, width: "100%" }}>
          <form onSubmit={handleSubmit}>
            {/* Row 1: Name + Visibility */}
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div className="admin-form-group" style={{ flex: "3 1 200px" }}>
                <label>Agent 名称 *</label>
                <input
                  className="admin-input"
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                  placeholder="例如：测试天气助手"
                />
              </div>
              <div className="admin-form-group" style={{ flex: "1 1 120px" }}>
                <label>可见性</label>
                <select
                  className="admin-select"
                  value={form.visibility}
                  onChange={(e) => update("visibility", e.target.value)}
                >
                  <option value="public">全员可见</option>
                  <option value="department">按部门</option>
                  <option value="specific">指定用户</option>
                </select>
              </div>
            </div>

            {/* Row 2: API Endpoint + Headers */}
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div className="admin-form-group" style={{ flex: "2 1 250px" }}>
                <label>API 地址 *</label>
                <input
                  className="admin-input"
                  value={form.api_endpoint}
                  onChange={(e) => update("api_endpoint", e.target.value)}
                  placeholder="http://localhost:9999"
                />
                <span style={{ fontSize: 11, color: "#999", marginTop: 4, display: "block" }}>
                  Agent API 服务地址，需实现 POST 接口，接收 {"{ messages, stream }"} 格式
                </span>
              </div>
              <div className="admin-form-group" style={{ flex: "1 1 200px" }}>
                <label>API Headers (JSON)</label>
                <textarea
                  className="admin-textarea"
                  value={form.api_headers}
                  onChange={(e) => update("api_headers", e.target.value)}
                  placeholder='{"Authorization": "Bearer xxx"}'
                />
              </div>
            </div>

            {/* Department visibility config */}
            {form.visibility === "department" && (
              <div className="admin-form-group">
                <label>选择可见部门 *</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  {DEPARTMENTS.map((dept) => (
                    <button
                      key={dept}
                      type="button"
                      className={`perm-chip${selectedDepts.includes(dept) ? " selected" : ""}`}
                      onClick={() => toggleDept(dept)}
                    >
                      {selectedDepts.includes(dept) && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                      )}
                      {dept}
                    </button>
                  ))}
                </div>
                <span style={{ fontSize: 11, color: "#999", marginTop: 6, display: "block" }}>
                  已选择 {selectedDepts.length} 个部门
                </span>
              </div>
            )}

            {/* Specific user visibility config */}
            {form.visibility === "specific" && (
              <div className="admin-form-group">
                <label>选择可见用户 *</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  {users.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      className={`perm-chip${selectedUserIds.includes(u.id) ? " selected" : ""}`}
                      onClick={() => toggleUser(u.id)}
                    >
                      {selectedUserIds.includes(u.id) && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                      )}
                      {u.name}
                      <span style={{ color: selectedUserIds.includes(u.id) ? "rgba(255,255,255,0.5)" : "#999", fontSize: 11 }}>
                        {u.department}
                      </span>
                    </button>
                  ))}
                </div>
                <span style={{ fontSize: 11, color: "#999", marginTop: 6, display: "block" }}>
                  已选择 {selectedUserIds.length} 个用户
                </span>
              </div>
            )}

            {err && <p className="error-text" style={{ marginBottom: 16 }}>{err}</p>}

            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
              <button type="submit" className="admin-btn admin-btn-primary" disabled={loading}>
                {loading ? "创建中..." : "发布"}
              </button>
              <button type="button" onClick={() => router.push("/agents")} className="admin-btn admin-btn-secondary">
                取消
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
