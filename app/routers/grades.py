from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import grade as grade_crud
from app.schemas.grade import GradeRead, GradeUpdate

router = APIRouter(prefix="/api/grades", tags=["grades"])


@router.patch("/{grade_id}", response_model=GradeRead)
def update_grade(
    grade_id: int,
    body: GradeUpdate,
    db: Session = Depends(get_db),
) -> GradeRead:
    row = grade_crud.get_by_id(db, grade_id)
    if row is None:
        raise HTTPException(status_code=404, detail="등급을 찾을 수 없습니다.")
    grade_crud.update(
        db,
        row,
        grade_name=body.grade_name.strip() if body.grade_name is not None else None,
        sort_order=body.sort_order,
    )
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{grade_id}", status_code=204)
def delete_grade(grade_id: int, db: Session = Depends(get_db)) -> None:
    row = grade_crud.get_by_id(db, grade_id)
    if row is None:
        raise HTTPException(status_code=404, detail="등급을 찾을 수 없습니다.")
    try:
        grade_crud.delete(db, row)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="이 등급에 연결된 재고 이력이 있어 삭제할 수 없습니다.",
        )
