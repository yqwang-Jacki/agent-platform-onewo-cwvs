"use client";

import { useEffect, useState, useCallback } from "react";
import {
  listAdminUsers,
  updateUserRole,
  updateUserStatus,
  updateUser,
  deleteUser,
  resetUserPassword,
  createUser,
  listRoles,
  AdminUser,
  RoleItem,
} from "@/lib/api";

const EMPTY_CREATE = {
  name: "", department: "", sap_id: "", phone: "", email: "", password: "", role: "user",
};

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  // Edit modal
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState({
    name: "", department: "", sap_id: "", phone: "", email: "", role: "", status: "",
  });
  const [editSaving, setEditSaving] = useState(false);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ ...EMPTY_CREATE });
  const [createSaving, setCreateSaving] = useState(false);

  // Import modal — simple CSV preview
  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState("");
  const [importPreview, setImportPreview] = useState<string[][]>([]);
  const [importSaving, setImportSaving] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listAdminUsers({
        role: roleFilter || undefined,
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setUsers(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter, statusFilter]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);
  useEffect(() => { listRoles().then(setRoles).catch(() => {}); }, []);

  function showToast(msg: string, type: "success" | "error") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }

  async function handleRoleChange(userId: string, role: string) {
    try {
      await updateUserRole(userId, role);
      showToast("角色已更新", "success");
      fetchUsers();
    } catch (e) {
      showToast((e as Error).message, "error");
    }
  }

  async function handleStatusToggle(user: AdminUser) {
    const newStatus = user.status === "active" ? "disabled" : "active";
    try {
      await updateUserStatus(user.id, newStatus);
      showToast(`用户已${newStatus === "active" ? "启用" : "禁用"}`, "success");
      fetchUsers();
    } catch (e) {
      showToast((e as Error).message, "error");
    }
  }

  async function handleResetPwd(userId: string) {
    if (!confirm("确认重置该用户密码？")) return;
    try {
      const res = await resetUserPassword(userId);
      showToast(`密码已重置为 ${res.new_password}`, "success");
    } catch (e) {
      showToast((e as Error).message, "error");
    }
  }

  function openEdit(u: AdminUser) {
    setEditUser(u);
    setEditForm({
      name: u.name, department: u.department, sap_id: u.sap_id,
      phone: u.phone, email: u.email, role: u.role, status: u.status,
    });
  }

  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editUser) return;
    setEditSaving(true);
    try {
      const changed: Record<string, string> = {};
      for (const [k, v] of Object.entries(editForm)) {
        if (v !== (editUser as Record<string, unknown>)[k]) changed[k] = v;
      }
      if (Object.keys(changed).length === 0) { setEditUser(null); return; }
      await updateUser(editUser.id, changed);
      showToast("用户信息已更新", "success");
      setEditUser(null);
      fetchUsers();
    } catch (e) {
      showToast((e as Error).message, "error");
    } finally {
      setEditSaving(false);
    }
  }

  async function handleDelete(user: AdminUser) {
    if (!confirm(`确认删除用户「${user.name}」？此操作将禁用该用户账号。`)) return;
    try {
      await deleteUser(user.id);
      showToast(`用户「${user.name}」已禁用`, "success");
      fetchUsers();
    } catch (e) {
      showToast((e as Error).message, "error");
    }
  }

  // ── Create user ──
  function openCreate() {
    setCreateForm({ ...EMPTY_CREATE, role: roles[0]?.key || "user" });
    setShowCreate(true);
  }

  async function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    setCreateSaving(true);
    try {
      await createUser(createForm);
      showToast(`用户「${createForm.name}」已创建`, "success");
      setShowCreate(false);
      fetchUsers();
    } catch (err) {
      showToast((err as Error).message, "error");
    } finally {
      setCreateSaving(false);
    }
  }

  // ── Batch import (CSV paste) ──
  function parseImportCSV() {
    const lines = importText.trim().split("\n").filter(Boolean);
    const rows = lines.map((line) => line.split(/[,\t]/).map((s) => s.trim()));
    setImportPreview(rows);
  }

  async function handleImportSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (importPreview.length === 0) return;
    setImportSaving(true);
    let created = 0;
    let failed = 0;
    for (const row of importPreview) {
      if (row.length < 7) { failed++; continue; }
      try {
        await createUser({
          name: row[0], department: row[1], sap_id: row[2],
          phone: row[3], email: row[4], password: row[5], role: row[6],
        });
        created++;
      } catch { failed++; }
    }
    showToast(`导入完成：成功 ${created}，失败 ${failed}`, created > 0 ? "success" : "error");
    setShowImport(false);
    setImportText("");
    setImportPreview([]);
    setImportSaving(false);
    fetchUsers();
  }

  return (
    <>
      {/* Header */}
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>用户管理</h1>
          <span className="admin-page-count">{users.length} 位用户</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="admin-btn admin-btn-secondary" onClick={() => setShowImport(true)}>
            批量导入
          </button>
          <button className="admin-btn admin-btn-primary" onClick={openCreate}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            新增用户
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="admin-content">
        <div className="admin-toolbar">
          <div className="admin-toolbar-filters">
            <input
              className="admin-input admin-input-search"
              placeholder="搜索姓名 / 手机号 / 邮箱..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button
              className="admin-btn-sm admin-filter-toggle"
              onClick={() => setShowFilters(!showFilters)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
              </svg>
              筛选
              {(roleFilter || statusFilter) && <span className="filter-dot" />}
            </button>
          </div>
          {showFilters && (
            <div className="admin-toolbar-filters-extended">
              <select
                className="admin-input admin-input-select"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
              >
                <option value="">全部角色</option>
                {roles.map((r) => (
                  <option key={r.key} value={r.key}>{r.label}</option>
                ))}
              </select>
              <select
                className="admin-input admin-input-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">全部状态</option>
                <option value="active">已启用</option>
                <option value="disabled">已禁用</option>
              </select>
            </div>
          )}
        </div>

        {toast && <div className={`admin-toast ${toast.type}`}>{toast.msg}</div>}

        {loading && <div className="loading-text">加载中...</div>}
        {error && <div className="error-text">{error}</div>}

        {!loading && !error && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>部门</th>
                  <th>SAP 工号</th>
                  <th>手机号</th>
                  <th>邮箱</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th className="col-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 && (
                  <tr>
                    <td colSpan={8} className="table-empty">
                      暂无用户数据
                    </td>
                  </tr>
                )}
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="cell-name">{u.name}</td>
                    <td className="cell-muted">{u.department}</td>
                    <td className="cell-mono">{u.sap_id}</td>
                    <td>{u.phone}</td>
                    <td className="cell-muted">{u.email}</td>
                    <td>
                      <select
                        className="cell-role-select"
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      >
                        {roles.map((r) => (
                          <option key={r.key} value={r.key}>{r.label}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${u.status === "active" ? "badge-success" : "badge-danger"}`}>
                        {u.status === "active" ? "启用" : "禁用"}
                      </span>
                    </td>
                    <td className="cell-actions">
                      <button className="admin-btn-sm" onClick={() => openEdit(u)}>编辑</button>
                      <button className="admin-btn-sm" onClick={() => handleStatusToggle(u)}>
                        {u.status === "active" ? "禁用" : "启用"}
                      </button>
                      <button className="admin-btn-sm" onClick={() => handleResetPwd(u.id)}>
                        重置密码
                      </button>
                      <button className="admin-btn-sm admin-btn-sm-danger" onClick={() => handleDelete(u)}>
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Edit Modal ── */}
      {editUser && (
        <div className="admin-modal-overlay" onClick={() => setEditUser(null)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3>编辑用户</h3>
              <button className="admin-modal-close" onClick={() => setEditUser(null)}>&times;</button>
            </div>
            <form onSubmit={handleEditSubmit}>
              <div className="admin-modal-body">
                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>姓名</label>
                    <input className="admin-input" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                  </div>
                  <div className="admin-form-group">
                    <label>部门</label>
                    <input className="admin-input" value={editForm.department} onChange={(e) => setEditForm({ ...editForm, department: e.target.value })} />
                  </div>
                </div>
                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>SAP 工号</label>
                    <input className="admin-input" value={editForm.sap_id} onChange={(e) => setEditForm({ ...editForm, sap_id: e.target.value })} />
                  </div>
                  <div className="admin-form-group">
                    <label>手机号</label>
                    <input className="admin-input" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
                  </div>
                </div>
                <div className="admin-form-group">
                  <label>邮箱</label>
                  <input className="admin-input" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
                </div>
                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>角色</label>
                    <select className="admin-input admin-input-select" value={editForm.role} onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}>
                      {roles.map((r) => (<option key={r.key} value={r.key}>{r.label}</option>))}
                    </select>
                  </div>
                  <div className="admin-form-group">
                    <label>状态</label>
                    <select className="admin-input admin-input-select" value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      <option value="active">已启用</option>
                      <option value="disabled">已禁用</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="admin-modal-footer">
                <button type="button" className="admin-btn admin-btn-secondary" onClick={() => setEditUser(null)}>取消</button>
                <button type="submit" className="admin-btn admin-btn-primary" disabled={editSaving}>
                  {editSaving ? "保存中..." : "保存"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Create Modal ── */}
      {showCreate && (
        <div className="admin-modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3>新增用户</h3>
              <button className="admin-modal-close" onClick={() => setShowCreate(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreateSubmit}>
              <div className="admin-modal-body">
                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>姓名 <span style={{ color: "#ef4444" }}>*</span></label>
                    <input className="admin-input" value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} required />
                  </div>
                  <div className="admin-form-group">
                    <label>部门 <span style={{ color: "#ef4444" }}>*</span></label>
                    <input className="admin-input" value={createForm.department} onChange={(e) => setCreateForm({ ...createForm, department: e.target.value })} required />
                  </div>
                </div>
                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>SAP 工号 <span style={{ color: "#ef4444" }}>*</span></label>
                    <input className="admin-input" value={createForm.sap_id} onChange={(e) => setCreateForm({ ...createForm, sap_id: e.target.value })} required />
                  </div>
                  <div className="admin-form-group">
                    <label>手机号 <span style={{ color: "#ef4444" }}>*</span></label>
                    <input className="admin-input" value={createForm.phone} onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })} required />
                  </div>
                </div>
                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>邮箱 <span style={{ color: "#ef4444" }}>*</span></label>
                    <input className="admin-input" type="email" value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} required />
                  </div>
                  <div className="admin-form-group">
                    <label>密码 <span style={{ color: "#ef4444" }}>*</span></label>
                    <input className="admin-input" type="text" value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} required minLength={8} placeholder="至少 8 位" />
                  </div>
                </div>
                <div className="admin-form-group" style={{ maxWidth: "calc(50% - 8px)" }}>
                  <label>角色</label>
                  <select className="admin-input admin-input-select" value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}>
                    {roles.map((r) => (<option key={r.key} value={r.key}>{r.label}</option>))}
                  </select>
                </div>
              </div>
              <div className="admin-modal-footer">
                <button type="button" className="admin-btn admin-btn-secondary" onClick={() => setShowCreate(false)}>取消</button>
                <button type="submit" className="admin-btn admin-btn-primary" disabled={createSaving}>
                  {createSaving ? "创建中..." : "创建用户"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Batch Import Modal ── */}
      {showImport && (
        <div className="admin-modal-overlay" onClick={() => setShowImport(false)}>
          <div className="admin-modal admin-modal-wide" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3>批量导入用户</h3>
              <button className="admin-modal-close" onClick={() => setShowImport(false)}>&times;</button>
            </div>
            <form onSubmit={handleImportSubmit}>
              <div className="admin-modal-body">
                <p className="form-hint" style={{ marginBottom: 12 }}>
                  每行一个用户，用逗号或 Tab 分隔：<br />
                  <code style={{ fontSize: 11, background: "#f5f5f5", padding: "1px 6px", borderRadius: 3 }}>
                    姓名,部门,SAP工号,手机号,邮箱,密码,角色key
                  </code>
                </p>
                <textarea
                  className="admin-textarea"
                  rows={8}
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder={"张三,技术部,EMP001,13800000003,zhang@example.com,Abc123456,user\n李四,产品部,EMP002,13800000004,li@example.com,Abc123456,developer"}
                  style={{ fontSize: 12 }}
                />
                <button
                  type="button"
                  className="admin-btn-sm"
                  style={{ marginTop: 8 }}
                  onClick={parseImportCSV}
                  disabled={!importText.trim()}
                >
                  预览
                </button>
                {importPreview.length > 0 && (
                  <div style={{ marginTop: 12, fontSize: 12, color: "#666" }}>
                    共检测到 <strong>{importPreview.length}</strong> 条记录
                    <div style={{ maxHeight: 120, overflow: "auto", marginTop: 6, background: "#fafafa", borderRadius: 6, padding: "8px 12px", border: "1px solid #eee" }}>
                      {importPreview.slice(0, 5).map((row, i) => (
                        <div key={i} style={{ padding: "2px 0", color: row.length < 7 ? "#ef4444" : "#333" }}>
                          {i + 1}. {row.slice(0, 3).join("  |  ")}...
                          {row.length < 7 && <span style={{ marginLeft: 8, color: "#ef4444" }}>（字段不足）</span>}
                        </div>
                      ))}
                      {importPreview.length > 5 && <div style={{ color: "#999", padding: "2px 0" }}>... 还有 {importPreview.length - 5} 条</div>}
                    </div>
                  </div>
                )}
              </div>
              <div className="admin-modal-footer">
                <button type="button" className="admin-btn admin-btn-secondary" onClick={() => setShowImport(false)}>取消</button>
                <button type="submit" className="admin-btn admin-btn-primary" disabled={importPreview.length === 0 || importSaving}>
                  {importSaving ? "导入中..." : `导入 ${importPreview.length || 0} 人`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
