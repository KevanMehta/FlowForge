from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import current_user, require_roles
from ..models import Schedule, User
from ..schemas.common import ScheduleCreate, ScheduleUpdate

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("")
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    schedule = Schedule(workflow_id=payload.workflow_id, created_by_id=user.id, name=payload.name, cron=payload.cron, run_at=payload.run_at, is_active=payload.is_active)
    db.add(schedule)
    db.commit()
    return {"id": str(schedule.id), "name": schedule.name, "is_active": schedule.is_active}


@router.get("")
def list_schedules(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": str(s.id), "workflow_id": str(s.workflow_id), "name": s.name, "cron": s.cron, "run_at": s.run_at, "is_active": s.is_active} for s in db.scalars(select(Schedule).order_by(Schedule.created_at.desc()))]


@router.patch("/{schedule_id}")
def update_schedule(schedule_id: str, payload: ScheduleUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)
    db.commit()
    return {"ok": True}


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_active = False
    db.commit()
    return {"ok": True}
