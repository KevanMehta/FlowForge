from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import current_user
from ..models import Role, User
from ..schemas.common import LoginRequest, TokenPair, UserCreate
from ..security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from ..services.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    role = db.scalar(select(Role).where(Role.name == payload.role)) or db.scalar(select(Role).where(Role.name == "developer"))
    user = User(email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password), role_id=role.id)
    db.add(user)
    db.flush()
    audit(db, user, "auth.register", "user", str(user.id))
    db.commit()
    return TokenPair(access_token=create_access_token(str(user.id), role.name), refresh_token=create_refresh_token(str(user.id)))


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    audit(db, user, "auth.login", "user", str(user.id))
    db.commit()
    return TokenPair(access_token=create_access_token(str(user.id), user.role.name), refresh_token=create_refresh_token(str(user.id)))


@router.post("/refresh", response_model=TokenPair)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token, "refresh")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return TokenPair(access_token=create_access_token(str(user.id), user.role.name), refresh_token=create_refresh_token(str(user.id)))


@router.post("/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    audit(db, user, "auth.logout", "user", str(user.id))
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role.name, "is_active": user.is_active}
