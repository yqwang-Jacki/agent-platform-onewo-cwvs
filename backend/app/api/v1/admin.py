"""
管理员 API：用户管理、角色管理
仅 admin 角色可访问；部分端点 developer 可读
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Publisher, Role
from app.core.security import (
    get_current_admin_user,
    require_role,
    get_valid_roles,
    get_role_hierarchy,
    get_role_labels,
    get_role_permissions,
    get_password_hash,
    _load_roles_from_db,
)
from app.schemas import (
    UserAdminItem,
    UserCreate,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
    RoleInfo,
    RoleItem,
    RoleCreate,
    RoleUpdate,
    MenuPermission,
)

router = APIRouter()


# ── Available menu permissions ─────────────────────
# These are all the menu/permission slots that can be assigned to roles

AVAILABLE_MENUS: list[dict] = [
    {"key": "chat", "label": "对话交互", "category": "用户端"},
    {"key": "history", "label": "查看历史记录", "category": "用户端"},
    {"key": "admin_login", "label": "登录管理后台", "category": "管理后台"},
    {"key": "agent_manage", "label": "发布/管理 Agent", "category": "管理后台"},
    {"key": "usage_stats", "label": "查看用量统计", "category": "管理后台"},
    {"key": "user_manage", "label": "用户管理", "category": "管理后台"},
    {"key": "role_manage", "label": "角色管理", "category": "管理后台"},
    {"key": "system_settings", "label": "系统设置", "category": "管理后台"},
]


def _refresh_role_cache(db: Session):
    """Refresh role cache after any mutation."""
    _load_roles_from_db(db)


# ── Menu permissions ──────────────────────────────

@router.get("/menus", response_model=list[MenuPermission])
def list_menus(
    _current: User = Depends(require_role("admin")),
):
    """列出所有可用菜单权限项（仅 admin）。"""
    return [MenuPermission(**m) for m in AVAILABLE_MENUS]


# ── Role management ───────────────────────────────

@router.get("/roles", response_model=list[RoleItem])
def list_roles(
    _current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """列出所有角色（仅 admin 可读写）。"""
    return db.query(Role).filter(Role.status == "active").order_by(Role.level.asc()).all()


@router.get("/roles/{role_id}", response_model=RoleItem)
def get_role(
    role_id: str,
    _current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    r = db.query(Role).filter(Role.id == role_id, Role.status == "active").first()
    if not r:
        raise HTTPException(404, "角色不存在")
    return r


@router.post("/roles", response_model=RoleItem, status_code=201)
def create_role(
    data: RoleCreate,
    _current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """创建自定义角色（仅 admin）。"""
    # Check key uniqueness
    if db.query(Role).filter(Role.key == data.key).first():
        raise HTTPException(400, f"角色标识 '{data.key}' 已存在")
    r = Role(
        key=data.key,
        label=data.label,
        description=data.description,
        level=data.level,
        permissions=data.permissions,
        is_system=False,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    _refresh_role_cache(db)
    return r


@router.put("/roles/{role_id}", response_model=RoleItem)
def update_role(
    role_id: str,
    data: RoleUpdate,
    _current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """编辑角色（仅 admin）。"""
    r = db.query(Role).filter(Role.id == role_id, Role.status == "active").first()
    if not r:
        raise HTTPException(404, "角色不存在")
    if data.label is not None:
        r.label = data.label
    if data.description is not None:
        r.description = data.description
    if data.level is not None:
        r.level = data.level
    if data.permissions is not None:
        r.permissions = data.permissions
    db.commit()
    db.refresh(r)
    _refresh_role_cache(db)
    return r


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: str,
    _current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """删除角色（仅 admin，系统角色不可删，有关联用户的角色不可删）。"""
    r = db.query(Role).filter(Role.id == role_id, Role.status == "active").first()
    if not r:
        raise HTTPException(404, "角色不存在")
    if r.is_system:
        raise HTTPException(400, "系统内置角色不可删除")
    # Check if any user has this role
    user_count = db.query(User).filter(User.role == r.key, User.status == "active").count()
    if user_count > 0:
        raise HTTPException(400, f"该角色下还有 {user_count} 个用户，请先迁移用户后再删除")
    r.status = "deleted"
    db.commit()
    _refresh_role_cache(db)
    return {"message": f"角色 '{r.label}' 已删除"}


# ── User management ──────────────────────────────────

@router.get("/users", response_model=list[UserAdminItem])
def list_users(
    role: str = Query(None, description="按角色筛选"),
    status: str = Query(None, description="按状态筛选"),
    search: str = Query(None, description="搜索姓名/手机号/邮箱"),
    _current_admin: User = Depends(require_role("developer")),
    db: Session = Depends(get_db),
):
    """列出所有用户（developer+ 可读，admin 可编辑）。"""
    q = db.query(User)
    valid_roles = get_valid_roles(db)
    if role and role in valid_roles:
        q = q.filter(User.role == role)
    if status and status in ("active", "disabled"):
        q = q.filter(User.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (User.name.ilike(like))
            | (User.phone.ilike(like))
            | (User.email.ilike(like))
        )
    return q.order_by(User.role.asc(), User.created_at.desc()).all()


@router.post("/users", response_model=UserAdminItem, status_code=201)
def create_user(
    data: UserCreate,
    _current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """创建用户（仅 admin）。"""
    valid_roles = get_valid_roles(db)
    if data.role not in valid_roles:
        raise HTTPException(400, f"无效角色: {data.role}，可选: {', '.join(valid_roles)}")

    # Check uniqueness
    if db.query(User).filter(User.sap_id == data.sap_id).first():
        raise HTTPException(400, f"SAP 工号 {data.sap_id} 已存在")
    if db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(400, f"手机号 {data.phone} 已存在")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, f"邮箱 {data.email} 已存在")

    u = User(
        name=data.name,
        department=data.department,
        sap_id=data.sap_id,
        phone=data.phone,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=data.role,
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.get("/users/{user_id}", response_model=UserAdminItem)
def get_user(
    user_id: str,
    _current_admin: User = Depends(require_role("developer")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    return u


@router.put("/users/{user_id}", response_model=UserAdminItem)
def update_user(
    user_id: str,
    data: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """编辑用户全部信息（仅 admin）。"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")

    # Validate role if provided
    if data.role is not None:
        valid_roles = get_valid_roles(db)
        if data.role not in valid_roles:
            raise HTTPException(400, f"无效角色: {data.role}")
        # Prevent self-role modification
        if u.id == current_admin.id and data.role != u.role:
            raise HTTPException(400, "不能修改自己的角色")
        u.role = data.role

    if data.name is not None:
        u.name = data.name
    if data.department is not None:
        u.department = data.department
    if data.sap_id is not None:
        existing = db.query(User).filter(User.sap_id == data.sap_id, User.id != user_id).first()
        if existing:
            raise HTTPException(400, f"SAP 工号 {data.sap_id} 已被其他用户使用")
        u.sap_id = data.sap_id
    if data.phone is not None:
        existing = db.query(User).filter(User.phone == data.phone, User.id != user_id).first()
        if existing:
            raise HTTPException(400, f"手机号 {data.phone} 已被其他用户使用")
        u.phone = data.phone
    if data.email is not None:
        existing = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(400, f"邮箱 {data.email} 已被其他用户使用")
        u.email = data.email
    if data.status is not None:
        if u.id == current_admin.id and data.status == "disabled":
            raise HTTPException(400, "不能禁用自己的账号")
        u.status = data.status

    db.commit()
    db.refresh(u)
    return u


@router.put("/users/{user_id}/role", response_model=UserAdminItem)
def update_user_role(
    user_id: str,
    data: UserRoleUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """修改用户角色（仅 admin）。"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    valid_roles = get_valid_roles(db)
    if data.role not in valid_roles:
        raise HTTPException(400, f"无效角色: {data.role}")
    if u.id == current_admin.id:
        raise HTTPException(400, "不能修改自己的角色")
    u.role = data.role
    db.commit()
    db.refresh(u)
    return u


@router.put("/users/{user_id}/status", response_model=UserAdminItem)
def update_user_status(
    user_id: str,
    data: UserStatusUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """启用/禁用用户（仅 admin）。"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    if u.id == current_admin.id:
        raise HTTPException(400, "不能禁用自己的账号")
    u.status = data.status
    db.commit()
    db.refresh(u)
    return u


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """重置用户密码为默认密码（仅 admin）。"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    default_pwd = "Abc123456"
    u.password_hash = get_password_hash(default_pwd)
    db.commit()
    return {"message": f"密码已重置为 {default_pwd}", "new_password": default_pwd}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """删除用户（仅 admin，不可删除自己）。"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    if u.id == current_admin.id:
        raise HTTPException(400, "不能删除自己的账号")
    # Soft-delete: mark as disabled
    u.status = "disabled"
    db.commit()
    return {"message": f"用户 '{u.name}' 已被禁用（软删除）"}


# ── Publisher list (for admin context) ────────────────

@router.get("/publishers")
def list_publishers(
    _current: User = Depends(require_role("developer")),
    db: Session = Depends(get_db),
):
    pubs = db.query(Publisher).order_by(Publisher.created_at.desc()).all()
    return [
        {
            "appid": p.appid,
            "name": p.name,
            "phone": p.phone,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        }
        for p in pubs
    ]
