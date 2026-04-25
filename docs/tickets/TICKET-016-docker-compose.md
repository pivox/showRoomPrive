# TICKET-016 — Mise à jour Docker Compose (API + Frontend)

**Epic:** Infrastructure  
**Priorité:** P2  
**Complexité:** S  
**Dépendances:** TICKET-001, TICKET-011

---

## Contexte

Le `docker-compose.yml` actuel expose uniquement le scraper CLI et la DB. On ajoute deux services : l'API FastAPI et le frontend Next.js. Le service `app` existant (scraper en boucle) est conservé mais rendu optionnel — le cron peut désormais être piloté via l'API.

---

## `docker-compose.yml` cible

```yaml
services:
  db:
    image: postgres:16
    container_name: showroom_db
    environment:
      POSTGRES_DB: showroom
      POSTGRES_USER: showroom
      POSTGRES_PASSWORD: showroom
    ports:
      - "55432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U showroom -d showroom"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: showroom_api
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - DATABASE_URL=postgresql+psycopg2://showroom:showroom@db:5432/showroom
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./playwright/.auth:/app/playwright/.auth
      - ./artifacts:/app/artifacts

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: showroom_frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api

  # Optionnel : scraper autonome (désactivé par défaut si le cron est géré via l'API)
  # app:
  #   build: .
  #   container_name: showroom_agent
  #   command: ["python", "-m", "src.app"]
  #   depends_on:
  #     db:
  #       condition: service_healthy
  #   env_file: .env

volumes:
  pgdata:
```

---

## `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

Activer le output standalone dans `frontend/next.config.ts` :
```typescript
const config: NextConfig = {
  output: 'standalone',
}
```

---

## `Dockerfile` backend (mise à jour)

Ajouter l'étape Alembic au démarrage via un script `entrypoint.sh` :

```bash
#!/bin/bash
set -e
alembic upgrade head
exec "$@"
```

```dockerfile
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## `.env.example` — nouvelles variables à documenter

```env
# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
CRON_AUTOSTART=false

# AI Providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_AI_API_KEY=
AI_PROVIDER_ORDER=claude,openai,gemini
AI_RESULT_TTL_HOURS=24

# Recherche web (pour le provider Claude)
TAVILY_API_KEY=
```

---

## Acceptance criteria

- [ ] `docker compose up --build` démarre les 3 services (db, api, frontend) sans erreur
- [ ] `GET http://localhost:8000/health` retourne 200
- [ ] `http://localhost:3000` charge le dashboard
- [ ] Le frontend communique correctement avec l'API (pas d'erreur CORS)
- [ ] `alembic upgrade head` s'exécute automatiquement au démarrage du service `api`
- [ ] Le volume `playwright/.auth` est partagé correctement (cookies persistés entre restarts)
- [ ] `docker compose up db api` (sans frontend) fonctionne en mode développement
