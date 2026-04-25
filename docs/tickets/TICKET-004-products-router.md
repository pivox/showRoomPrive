# TICKET-004 — Router /products (liste + top 10)

**Epic:** Backend API Foundation  
**Priorité:** P1  
**Complexité:** S  
**Dépendances:** TICKET-001

---

## Contexte

Le frontend a besoin de lister les produits en DB avec filtres/pagination, et d'afficher le top 10 des meilleures remises réelles du dernier scan.

---

## Endpoints

### `GET /products`

Liste paginée de tous les produits.

**Query params :**

| Param | Type | Défaut | Description |
|---|---|---|---|
| `page` | int | 1 | Numéro de page |
| `page_size` | int | 50 | Max 200 |
| `brand` | str | — | Filtre exact sur `brand` (case-insensitive) |
| `min_discount` | float | — | `real_discount >= min_discount` |
| `max_price` | float | — | `showroom_price <= max_price` |
| `interesting_only` | bool | false | `is_interesting = true` uniquement |
| `sort` | str | `last_checked_at` | `last_checked_at` \| `real_discount` \| `showroom_price` |
| `order` | str | `desc` | `asc` \| `desc` |

**Réponse 200 :**
```json
{
  "total": 342,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "id": 1,
      "source_product_id": "98765",
      "name": "Sac cuir Milano",
      "brand": "Longchamp",
      "showroom_price": 89.00,
      "displayed_discount": 60.0,
      "brand_price": 250.00,
      "real_discount": 64.40,
      "product_url": "https://...",
      "is_interesting": true,
      "first_seen_at": "2026-04-25T08:00:00Z",
      "last_checked_at": "2026-04-25T10:00:00Z",
      "ai_status": "done"   // null | "pending" | "running" | "done" | "error"
    }
  ]
}
```

---

### `GET /products/top10`

Retourne les 10 produits avec la plus haute `real_discount`, parmi ceux dont `is_interesting = true`.

Pas de paramètre. Réponse : même structure qu'un item de `/products` dans un tableau de 10 éléments max.

```json
[{ ... }, { ... }]
```

---

## Implémentation

### Schéma Pydantic

```python
# src/api/schemas/product.py
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class ProductOut(BaseModel):
    id: int
    source_product_id: str | None
    name: str
    brand: str | None
    showroom_price: Decimal
    displayed_discount: Decimal | None
    brand_price: Decimal | None
    real_discount: Decimal | None
    product_url: str | None
    is_interesting: bool
    first_seen_at: datetime
    last_checked_at: datetime
    ai_status: str | None = None

    model_config = {"from_attributes": True}

class ProductListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductOut]
```

### Router

```python
# src/api/routers/products.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, asc
from src.api.deps import get_db, get_settings
from src.api.schemas.product import ProductOut, ProductListOut
from src.models import Product

router = APIRouter()

@router.get("/top10", response_model=list[ProductOut])
def top10(db=Depends(get_db)):
    stmt = (
        select(Product)
        .where(Product.is_interesting == True)
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
    sort: str = Query("last_checked_at", pattern="^(last_checked_at|real_discount|showroom_price)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db=Depends(get_db),
):
    stmt = select(Product)

    if brand:
        stmt = stmt.where(func.lower(Product.brand) == brand.lower())
    if min_discount is not None:
        stmt = stmt.where(Product.real_discount >= min_discount)
    if max_price is not None:
        stmt = stmt.where(Product.showroom_price <= max_price)
    if interesting_only:
        stmt = stmt.where(Product.is_interesting == True)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    sort_col = getattr(Product, sort)
    stmt = stmt.order_by(desc(sort_col) if order == "desc" else asc(sort_col))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    items = db.execute(stmt).scalars().all()
    return ProductListOut(total=total, page=page, page_size=page_size, items=items)
```

> **Note :** le champ `ai_status` sera peuplé via une jointure avec `ai_research_jobs` une fois le TICKET-005 livré. En attendant, retourner `None`.

---

## Acceptance criteria

- [ ] `GET /products/top10` retourne au plus 10 produits triés par `real_discount` décroissant
- [ ] `GET /products` pagine correctement avec `total` exact
- [ ] Filtres `brand`, `min_discount`, `max_price`, `interesting_only` fonctionnent en combinaison
- [ ] Tri par `real_discount`, `showroom_price`, `last_checked_at` dans les deux sens
- [ ] `page_size` > 200 retourne 422
- [ ] Aucune requête N+1 (pas de lazy load)
