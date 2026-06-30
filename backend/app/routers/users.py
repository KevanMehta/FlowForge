from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_roles
from ..models import Role, User
from ..services.audit import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role.name, "is_active": u.is_active} for u in db.scalars(select(User).order_by(User.email))]


@router.get("/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role.name, "is_active": user.is_active}


@router.patch("/{user_id}/role")
def patch_role(user_id: str, role: str, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    user = db.get(User, user_id)
    next_role = db.scalar(select(Role).where(Role.name == role))
    if not user or not next_role:
        raise HTTPException(status_code=404, detail="User or role not found")
    user.role_id = next_role.id
    audit(db, admin, "users.patch_role", "user", user_id, {"role": role})
    db.commit()
    return {"ok": True}
