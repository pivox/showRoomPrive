# TICKET-005 — Migration DB : table ai_research_jobs + Alembic

**Epic:** AI Research Worker  
**Priorité:** P0 (bloquant pour TICKET-006 à TICKET-010)  
**Complexité:** S  
**Dépendances:** TICKET-001

---

## Contexte

Les analyses IA sont des jobs asynchrones. Leurs résultats doivent être persistés pour être consultés après coup et éviter de re-analyser un même produit inutilement. On introduit Alembic pour gérer les migrations proprement dès maintenant.

---

## Tâches

### 1. Ajouter Alembic

```bash
pip install alembic==1.13.2
alembic init alembic
```

Configurer `alembic/env.py` pour utiliser `src.models.Base` et lire `DATABASE_URL` depuis l'environnement.

Ajouter dans `requirements.txt` :
```
alembic==1.13.2
```

### 2. Modèle SQLAlchemy

Ajouter dans `src/models.py` :

```python
import enum
from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, SmallInteger

class AIJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done    = "done"
    error   = "error"

class AIResearchJob(Base):
    __tablename__ = "ai_research_jobs"

    id          : Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    product_id  : Mapped[int]           = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    provider    : Mapped[str]           = mapped_column(String(50), nullable=False)  # "claude" | "openai" | "gemini"
    status      : Mapped[AIJobStatus]   = mapped_column(SAEnum(AIJobStatus), nullable=False, default=AIJobStatus.pending)
    is_real_deal: Mapped[bool | None]   = mapped_column(Boolean, nullable=True)
    confidence  : Mapped[int | None]    = mapped_column(SmallInteger, nullable=True)  # 0-100
    real_market_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    sources     : Mapped[dict | None]   = mapped_column(JSON, nullable=True)  # list[str]
    summary     : Mapped[str | None]    = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None]    = mapped_column(Text, nullable=True)
    created_at  : Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_utc_now)
    finished_at : Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="ai_jobs")
```

Ajouter la relation inverse dans `Product` :
```python
ai_jobs: Mapped[list["AIResearchJob"]] = relationship("AIResearchJob", back_populates="product", cascade="all, delete-orphan")
```

### 3. Migration Alembic

```bash
alembic revision --autogenerate -m "add ai_research_jobs table"
alembic upgrade head
```

Vérifier que la migration générée contient :
- Création de la table `ai_research_jobs`
- Index sur `product_id`
- Enum `aijobstatus` (ou colonne TEXT avec contrainte CHECK selon le driver)

### 4. Index supplémentaire

Ajouter manuellement dans la migration :
```python
op.create_index("idx_ai_jobs_product_status", "ai_research_jobs", ["product_id", "status"])
```

---

## Schéma résultant

```sql
CREATE TABLE ai_research_jobs (
  id                SERIAL PRIMARY KEY,
  product_id        INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  provider          VARCHAR(50) NOT NULL,
  status            VARCHAR(10) NOT NULL DEFAULT 'pending',
  is_real_deal      BOOLEAN,
  confidence        SMALLINT,
  real_market_price NUMERIC(10,2),
  sources           JSONB,
  summary           TEXT,
  raw_response      TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at       TIMESTAMPTZ
);

CREATE INDEX idx_ai_jobs_product_status ON ai_research_jobs(product_id, status);
```

---

## Acceptance criteria

- [ ] `alembic upgrade head` s'exécute sans erreur sur une DB vierge et sur une DB existante avec des produits
- [ ] `alembic downgrade -1` supprime proprement la table
- [ ] La relation `Product.ai_jobs` est accessible sans requête supplémentaire quand elle est chargée explicitement
- [ ] La contrainte `ON DELETE CASCADE` est effective (supprimer un produit supprime ses jobs)
- [ ] `init_db()` existant reste compatible (idempotent sur la table `products`)
