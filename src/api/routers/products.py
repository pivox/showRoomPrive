from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import selectinload

from src.api.deps import get_db
from src.api.schemas.product import ProductListOut, ProductOut
from src.models import AIResearchJob, Product

router = APIRouter()


def _latest_ai_status(product_ids: list[int], db) -> dict[int, str]:
    """Returns {product_id: latest ai job status} for the given product IDs."""
    if not product_ids:
        return {}
    # Subquery: rank jobs by created_at desc, take rank=1 per product
    ranked = (
        select(
            AIResearchJob.product_id,
            AIResearchJob.status,
            func.row_number()
            .over(
                partition_by=AIResearchJob.product_id,
                order_by=desc(AIResearchJob.created_at),
            )
            .label("rn"),
        )
        .where(AIResearchJob.product_id.in_(product_ids))
        .subquery()
    )
    rows = db.execute(
        select(ranked.c.product_id, ranked.c.status).where(ranked.c.rn == 1)
    ).all()
    return {row.product_id: row.status for row in rows}


def _to_out(product: Product, ai_statuses: dict[int, str]) -> ProductOut:
    status = ai_statuses.get(product.id)
    return ProductOut(
        id=product.id,
        source_product_id=product.source_product_id,
        name=product.name,
        brand=product.brand,
        showroom_price=product.showroom_price,
        displayed_discount=product.displayed_discount,
        brand_price=product.brand_price,
        real_discount=product.real_discount,
        product_url=product.product_url,
        is_interesting=product.is_interesting,
        first_seen_at=product.first_seen_at,
        last_checked_at=product.last_checked_at,
        ai_status=status.value if status is not None else None,
    )


@router.get("/top10", response_model=list[ProductOut])
def top10(db=Depends(get_db)):
    stmt = (
        select(Product)
        .where(Product.is_interesting == True)  # noqa: E712
        .where(Product.real_discount.isnot(None))
        .order_by(desc(Product.real_discount))
        .limit(10)
    )
    products = db.execute(stmt).scalars().all()
    ai_statuses = _latest_ai_status([p.id for p in products], db)
    return [_to_out(p, ai_statuses) for p in products]


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
    products = db.execute(paged).scalars().all()

    ai_statuses = _latest_ai_status([p.id for p in products], db)
    items = [_to_out(p, ai_statuses) for p in products]

    return ProductListOut(total=total, page=page, page_size=page_size, items=items)
