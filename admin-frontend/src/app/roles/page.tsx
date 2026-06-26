"use client";

import { useEffect, useState } from "react";
import {
  listRoles,
  createRole,
  updateRole,
  deleteRole,
  listMenus,
  RoleItem,
  MenuPermission,
} from "@/lib/api";

export default function RolesPage() {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [menus, setMenus] = useState<MenuPermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleItem | null>(null);
  const [form, setForm] = useState({
    key: "", label: "", description: "", level: 0, permissions: [] as string[],
  });
  const [saving, setSaving] = useState(false);

  async function fetchRoles() {
    try {
      setRoles(await listRoles());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRoles();
    listMenus().then(setMenus).catch(() => {});
  }, []);

  function showToast(msg: string, type: "success" | "error") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }

  function openCreate() {
    setEditingRole(null);
    setForm({ key: "", label: "", description: "", level: 0, permissions: [] });
    setModalOpen(true);
  }

  function openEdit(r: RoleItem) {
    setEditingRole(r);
    setForm({
      key: r.key, label: r.label, description: r.description,
      level: r.level, permissions: [...r.permissions],
    });
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingRole(null);
  }

  function togglePerm(label: string) {
    setForm((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(label)
        ? prev.permissions.filter((p) => p !== label)
        : [...prev.permissions, label],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingRole) {
        await updateRole(editingRole.id, {
          label: form.label, description: form.description,
          level: form.level, permissions: form.permissions,
        });
        showToast(`角色「${form.label}」已更新`, "success");
      } else {
        await createRole(form);
        showToast(`角色「${form.label}」已创建`, "success");
      }
      closeModal();
      fetchRoles();
    } catch (e) {
      showToast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(r: RoleItem) {
    if (!confirm(`确认删除角色「${r.label}」？`)) return;
    try {
      await deleteRole(r.id);
      showToast(`角色「${r.label}」已删除`, "success");
      fetchRoles();
    } catch (e) {
      showToast((e as Error).message, "error");
    }
  }

  // Group menus by category
  const menuGroups: Record<string, MenuPermission[]> = {};
  for (const m of menus) {
    const cat = m.category || "其他";
    if (!menuGroups[cat]) menuGroups[cat] = [];
    menuGroups[cat].push(m);
  }

  return (
    <>
      {/* Header */}
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>角色管理</h1>
          <span className="admin-page-count">{roles.length} 个角色</span>
        </div>
        <button className="admin-btn admin-btn-primary" onClick={openCreate}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建角色
        </button>
      </div>

      {/* Content */}
      <div className="admin-content">
        {toast && <div className={`admin-toast ${toast.type}`}>{toast.msg}</div>}

        {loading && <div className="loading-text">加载中...</div>}
        {error && <div className="error-text">{error}</div>}

        {!loading && !error && (
          <>
            {roles.length === 0 && (
              <div className="empty-text">暂无角色，点击右上角「新建角色」创建</div>
            )}

            <div className="role-grid">
              {roles.map((role) => (
                <div key={role.id} className="admin-card role-card">
                  {/* Top Row */}
                  <div className="role-card-top">
                    <div className="role-card-info">
                      <div className="role-card-title-row">
                        <h3 className="role-card-title">{role.label}</h3>
                        <span className="role-card-key">{role.key}</span>
                        {role.is_system && (
                          <span className="badge badge-warning">系统</span>
                        )}
                      </div>
                      {role.description && (
                        <p className="role-card-desc">{role.description}</p>
                      )}
                    </div>

                    <div className="role-card-actions">
                      <button className="admin-btn-sm" onClick={() => openEdit(role)}>
                        编辑
                      </button>
                      {!role.is_system && (
                        <button
                          className="admin-btn-sm admin-btn-sm-danger"
                          onClick={() => handleDelete(role)}
                        >
                          删除
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Permissions */}
                  <div className="role-card-perms">
                    <div className="role-card-perms-label">
                      拥有 {role.permissions.length} 项权限
                    </div>
                    {role.permissions.length > 0 ? (
                      <div className="role-card-perms-list">
                        {role.permissions.map((perm) => (
                          <span key={perm} className="role-card-perm-tag">{perm}</span>
                        ))}
                      </div>
                    ) : (
                      <span className="role-card-perms-empty">无任何权限</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Create / Edit Modal */}
      {modalOpen && (
        <div className="admin-modal-overlay" onClick={closeModal}>
          <div className="admin-modal admin-modal-wide" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3>{editingRole ? `编辑「${editingRole.label}」` : "新建角色"}</h3>
              <button className="admin-modal-close" onClick={closeModal}>&times;</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="admin-modal-body">
                {/* Basic Info */}
                <div className="admin-form-section-label">基本信息</div>

                <div className="admin-form-row">
                  <div className="admin-form-group">
                    <label>
                      角色标识 <span className="form-label-hint">英文 key</span>
                    </label>
                    <input
                      className="admin-input"
                      value={form.key}
                      onChange={(e) => setForm({ ...form, key: e.target.value })}
                      disabled={!!editingRole}
                      placeholder="e.g. editor"
                      required
                    />
                    {editingRole && (
                      <span className="form-hint">标识创建后不可修改</span>
                    )}
                  </div>
                  <div className="admin-form-group">
                    <label>
                      层级权重 <span className="form-label-hint">数值越大权限越高</span>
                    </label>
                    <input
                      className="admin-input"
                      type="number"
                      value={form.level}
                      onChange={(e) => setForm({ ...form, level: parseInt(e.target.value) || 0 })}
                      required
                    />
                  </div>
                </div>

                <div className="admin-form-group">
                  <label>角色名称</label>
                  <input
                    className="admin-input"
                    value={form.label}
                    onChange={(e) => setForm({ ...form, label: e.target.value })}
                    placeholder="e.g. 内容编辑"
                    required
                  />
                </div>

                <div className="admin-form-group">
                  <label>角色描述</label>
                  <input
                    className="admin-input"
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="简短描述该角色的职责"
                  />
                </div>

                {/* Permissions */}
                <div className="admin-form-section-label">菜单权限</div>
                <p className="form-hint" style={{ marginTop: -4 }}>
                  勾选该角色可访问的菜单项
                </p>

                {Object.entries(menuGroups).length === 0 && (
                  <div className="loading-text" style={{ padding: 20 }}>加载菜单中...</div>
                )}

                {Object.entries(menuGroups).map(([category, items]) => (
                  <div key={category} className="perm-group">
                    <div className="perm-group-label">{category}</div>
                    <div className="perm-group-grid">
                      {items.map((m) => {
                        const checked = form.permissions.includes(m.label);
                        return (
                          <label
                            key={m.key}
                            className={`perm-chip ${checked ? "perm-chip-on" : ""}`}
                            onClick={() => togglePerm(m.label)}
                          >
                            <span className="perm-chip-dot">
                              {checked && (
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                              )}
                            </span>
                            {m.label}
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="admin-modal-footer">
                <button type="button" className="admin-btn admin-btn-secondary" onClick={closeModal}>
                  取消
                </button>
                <button type="submit" className="admin-btn admin-btn-primary" disabled={saving}>
                  {saving ? "保存中..." : editingRole ? "保存修改" : "创建角色"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
