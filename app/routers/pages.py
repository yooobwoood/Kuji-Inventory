from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from pydantic import ValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import pwd_context
from app.crud import grade as grade_crud
from app.crud import inventory as inventory_crud
from app.crud import product as product_crud
from app.crud import user as user_crud
from app.models.inventory_log import InventoryLog
from app.schemas.inventory import ChangeType, InventoryAdjust
from app.services.inventory_service import (
    InventoryAdjustmentError,
    adjust_inventory,
    process_draw_results,
)

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def _group_stock_by_product(rows: list) -> list[dict]:
    """(KujiProduct, KujiGrade) 튜플 목록을 상품 단위로 묶음."""
    order: list[int] = []
    buckets: dict[int, dict] = {}
    for p, g in rows:
        if p.id not in buckets:
            buckets[p.id] = {"product": p, "grades": []}
            order.append(p.id)
        buckets[p.id]["grades"].append(g)
    return [buckets[pid] for pid in order]


def _safe_next(next_path: str, default: str) -> str:
    if next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return default


def _redirect(path: str, **query: str) -> RedirectResponse:
    if query:
        q = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in query.items() if v)
        path = f"{path}?{q}" if q else path
    return RedirectResponse(url=path, status_code=303)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    rows = inventory_crud.list_current_stock(db)
    users = user_crud.list_active_users(db)
    by_product = _group_stock_by_product(rows)
    total_grades = sum(len(b["grades"]) for b in by_product)
    total_units = sum(g.current_stock for b in by_product for g in b["grades"])
    zero_grades = [
        (b["product"], g)
        for b in by_product
        for g in b["grades"]
        if g.current_stock == 0
    ]
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "대시보드",
            "by_product": by_product,
            "users": users,
            "total_products": len(by_product),
            "total_grades": total_grades,
            "total_units": total_units,
            "zero_grades": zero_grades,
            "nav_active": "home",
        },
    )


@router.get("/products", response_class=HTMLResponse)
def products_list(
    request: Request,
    db: Session = Depends(get_db),
    saved: str | None = None,
    error: str | None = None,
):
    items = product_crud.list_products(db, active_only=False)
    return templates.TemplateResponse(
        request,
        "products_list.html",
        {
            "title": "상품",
            "items": items,
            "saved": saved,
            "error": error,
            "nav_active": "products",
        },
    )


@router.post("/products")
def products_create(
    name: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    name = name.strip()
    if not name:
        return _redirect("/products", error="상품 이름을 입력해 주세요.")
    if product_crud.get_by_name(db, name):
        return _redirect("/products", error="이미 같은 이름의 상품이 있습니다.")
    try:
        product_crud.create(db, name=name, description=description.strip() if description else None)
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/products", error="상품을 저장할 수 없습니다.")
    return _redirect("/products", saved="1")


@router.post("/products/{product_id}/status")
def product_set_status(
    product_id: int,
    is_active: int = Form(...),
    next: str = Form("/products"),
    db: Session = Depends(get_db),
):
    row = product_crud.get_by_id(db, product_id)
    if row is None:
        return _redirect("/products", error="상품을 찾을 수 없습니다.")
    product_crud.update(db, row, name=None, is_active=bool(is_active))
    db.commit()
    return RedirectResponse(url=_safe_next(next, "/products"), status_code=303)


@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    saved: str | None = None,
    error: str | None = None,
):
    product = product_crud.get_by_id(db, product_id)
    if product is None:
        return _redirect("/products", error="상품을 찾을 수 없습니다.")
    grades = grade_crud.list_by_product(db, product_id)
    return templates.TemplateResponse(
        request,
        "product_detail.html",
        {
            "title": product.name,
            "product": product,
            "grades": grades,
            "saved": saved,
            "error": error,
            "nav_active": "products",
        },
    )


@router.post("/products/{product_id}/grades")
def product_add_grade(
    product_id: int,
    grade_code: str = Form(...),
    grade_name: str = Form(...),
    sort_order: int = Form(0),
    initial_stock: int = Form(0),
    db: Session = Depends(get_db),
):
    product = product_crud.get_by_id(db, product_id)
    if product is None:
        return _redirect("/products", error="상품을 찾을 수 없습니다.")
    code = grade_code.strip()
    gname = grade_name.strip()
    if not code or not gname:
        return _redirect(f"/products/{product_id}", error="등급 코드와 이름을 입력해 주세요.")
    if grade_crud.get_by_product_and_code(db, product_id, code):
        return _redirect(f"/products/{product_id}", error="같은 등급 코드가 이미 있습니다.")
    try:
        grade_crud.create(
            db,
            product_id=product_id,
            grade_code=code,
            grade_name=gname,
            sort_order=sort_order,
            initial_stock=max(0, initial_stock),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect(f"/products/{product_id}", error="등급을 저장할 수 없습니다.")
    return _redirect(f"/products/{product_id}", saved="1")


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    db: Session = Depends(get_db),
    error: str | None = None,
    ok: str | None = None,
    draw_ok: str | None = None,
):
    rows = inventory_crud.list_current_stock(db)
    users = user_crud.list_active_users(db)
    by_product = _group_stock_by_product(rows)
    return templates.TemplateResponse(
        request,
        "inventory.html",
        {
            "title": "재고 조정",
            "by_product": by_product,
            "users": users,
            "error": error,
            "ok": ok,
            "draw_ok": draw_ok,
            "nav_active": "inventory",
        },
    )


@router.post("/inventory")
def inventory_adjust(
    grade_id: int = Form(...),
    change_type: str = Form(...),
    quantity: int = Form(...),
    user_id: int = Form(...),
    reason: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        ct = ChangeType(change_type)
        payload = InventoryAdjust(
            grade_id=grade_id,
            change_type=ct,
            quantity=quantity,
            reason=reason.strip() if reason else None,
            user_id=user_id,
        )
        adjust_inventory(db, payload)
    except ValidationError as e:
        db.rollback()
        err = e.errors()[0].get("msg", "입력값을 확인해 주세요.") if e.errors() else "입력값을 확인해 주세요."
        return _redirect("/inventory", error=str(err))
    except ValueError as e:
        db.rollback()
        return _redirect("/inventory", error=str(e))
    except InventoryAdjustmentError as e:
        db.rollback()
        return _redirect("/inventory", error=e.message)
    return _redirect("/inventory", ok="1")


@router.post("/inventory/draw")
def inventory_draw_result(
    product_id: int = Form(...),
    draw_code: list[str] = Form([]),
    draw_qty: list[str] = Form([]),
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if len(draw_code) != len(draw_qty):
        return _redirect("/inventory", error="입력 행이 올바르지 않습니다.")

    parsed_codes: list[str] = []
    total_quantity = 0
    for code_raw, qty_raw in zip(draw_code, draw_qty):
        code = (code_raw or "").strip()
        qty_text = (qty_raw or "").strip()
        if not code and not qty_text:
            continue
        if not code:
            return _redirect("/inventory", error="등급 코드를 입력해 주세요.")
        try:
            qty = int(qty_text)
        except ValueError:
            return _redirect("/inventory", error="수량은 숫자로 입력해 주세요.")
        if qty < 1:
            return _redirect("/inventory", error="수량은 1 이상이어야 합니다.")
        parsed_codes.extend([code] * qty)
        total_quantity += qty

    if total_quantity < 1:
        return _redirect("/inventory", error="최소 1개 이상의 결과를 입력해 주세요.")

    try:
        process_draw_results(
            db,
            product_id=product_id,
            user_id=user_id,
            quantity=total_quantity,
            result_codes=parsed_codes,
        )
    except InventoryAdjustmentError as e:
        db.rollback()
        return _redirect("/inventory", error=e.message)
    return _redirect("/inventory", draw_ok="1")


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, db: Session = Depends(get_db)):
    stmt = (
        select(InventoryLog)
        .options(
            joinedload(InventoryLog.user),
            joinedload(InventoryLog.product),
            joinedload(InventoryLog.grade),
        )
        .order_by(InventoryLog.created_at.desc())
        .limit(150)
    )
    logs = list(db.execute(stmt).scalars().unique().all())
    return templates.TemplateResponse(
        request,
        "logs.html",
        {"title": "재고 이력", "logs": logs, "nav_active": "logs"},
    )


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db), saved: str | None = None, error: str | None = None):
    users = user_crud.list_active_users(db)
    return templates.TemplateResponse(
        request,
        "users.html",
        {
            "title": "사용자",
            "users": users,
            "saved": saved,
            "error": error,
            "nav_active": "users",
        },
    )


@router.post("/users")
def users_create(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    uname = username.strip()
    if not uname or len(password) < 4:
        return _redirect("/users", error="사용자명과 비밀번호(4자 이상)를 확인해 주세요.")
    if user_crud.get_by_username(db, uname):
        return _redirect("/users", error="이미 같은 사용자명이 있습니다.")
    try:
        user_crud.create(db, username=uname, password_hash=pwd_context.hash(password))
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/users", error="사용자를 저장할 수 없습니다.")
    return _redirect("/users", saved="1")
