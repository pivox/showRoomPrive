from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, desc, func, select

from src.api.deps import get_db
from src.api.schemas.product import ProductListOut, ProductOut
from src.models import Product

router = APIRouter()


@router.get("/top10", response_model=list[ProductOut])
def top10(db=Depends(get_db)):
    stmt = (
        select(Product)
        .where(Product.is_interesting == True)  # noqa: E712
        .where(Product.real_discount.isnot(None))
        .order_by(desc(Product.real_discount))
        .limit(10)
    )
    return db.execute(stmt).scalars().all()


@router.get("", response_model=ProductListOut)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    brand: str | None = None,
    min_discount: float | None = None,
    max_price: float | None = None,
    interesting_only: bool = False,
    sort: str = Query(
        "last_checked_at",
        pattern="^(last_checked_at|real_discount|showroom_price)$",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db=Depends(get_db),
):
    base = select(Product)
    if brand:
        base = base.where(func.lower(Product.brand) == brand.lower())
    if min_discount is not None:
        base = base.where(Product.real_discount >= min_discount)
    if max_price is not None:
        base = base.where(Product.showroom_price <= max_price)
    if interesting_only:
        base = base.where(Product.is_interesting == True)  # noqa: E712

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

    sort_col = getattr(Product, sort)
    ordered = base.order_by(desc(sort_col) if order == "desc" else asc(sort_col))
    paged = ordered.offset((page - 1) * page_size).limit(page_size)
    items = db.execute(paged).scalars().all()

    return ProductListOut(total=total, page=page, page_size=page_size, items=items)
