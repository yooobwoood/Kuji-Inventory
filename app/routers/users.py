"""로컬/단일 매장 초기 설정용: 첫 관리자 계정 생성. 운영 시에는 인증과 함께 정리하세요."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import pwd_context
from app.crud import user as user_crud
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if user_crud.get_by_username(db, body.username.strip()):
        raise HTTPException(status_code=409, detail="이미 같은 사용자명이 있습니다.")
    try:
        row = user_crud.create(
            db,
            username=body.username.strip(),
            password_hash=pwd_context.hash(body.password),
        )
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="사용자를 저장할 수 없습니다.")
