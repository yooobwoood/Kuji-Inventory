from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import grade as grade_crud
from app.crud import product as product_crud
from app.schemas.grade import GradeCreate, GradeRead
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, ProductWithGrades

router = APIRouter(prefix="/api/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    if product_crud.get_by_name(db, body.name.strip()):
        raise HTTPException(status_code=409, detail="이미 같은 이름의 상품이 있습니다.")
    try:
        row = product_crud.create(db, name=body.name.strip(), description=body.description)
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="상품을 저장할 수 없습니다.")


@router.get("", response_model=list[ProductRead])
def list_products(
    active_only: bool = Query(True, description="true면 활성 상품만"),
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    return product_crud.list_products(db, active_only=active_only)


@router.get("/{product_id}", response_model=ProductWithGrades)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductWithGrades:
    row = product_crud.get_by_id(db, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    grades = grade_crud.list_by_product(db, product_id)
    return ProductWithGrades.model_validate(
        {**ProductRead.model_validate(row).model_dump(), "grades": grades}
    )


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
) -> ProductRead:
    row = product_crud.get_by_id(db, product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    if body.name is not None:
        existing = product_crud.get_by_name(db, body.name.strip())
        if existing is not None and existing.id != product_id:
            raise HTTPException(status_code=409, detail="이미 같은 이름의 상품이 있습니다.")
    try:
        product_crud.update(
            db,
            row,
            name=body.name.strip() if body.name is not None else None,
            is_active=body.is_active,
        )
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="상품을 수정할 수 없습니다.")


@router.post("/{product_id}/grades", response_model=GradeRead, status_code=201)
def create_grade(
    product_id: int,
    body: GradeCreate,
    db: Session = Depends(get_db),
) -> GradeRead:
    product = product_crud.get_by_id(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    if grade_crud.get_by_product_and_code(db, product_id, body.grade_code.strip()):
        raise HTTPException(status_code=409, detail="이 상품에 같은 등급 코드가 이미 있습니다.")
    try:
        row = grade_crud.create(
            db,
            product_id=product_id,
            grade_code=body.grade_code.strip(),
            grade_name=body.grade_name.strip(),
            sort_order=body.sort_order,
            initial_stock=body.initial_stock,
        )
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="등급을 저장할 수 없습니다.")
