# TICKET-011 — Scaffold frontend Next.js + client API

**Epic:** Frontend  
**Priorité:** P1 — bloquant pour TICKET-012 à TICKET-015  
**Complexité:** M  
**Dépendances:** TICKET-001

---

## Contexte

Mise en place du projet Next.js avec le layout commun, le client HTTP typé vers l'API FastAPI, et la configuration de base. Aucune page fonctionnelle dans ce ticket — juste la fondation.

---

## Stack

```
Next.js 14 (App Router)
TypeScript
Tailwind CSS
shadcn/ui  (composants)
TanStack Query v5  (data fetching + polling)
```

---

## Structure cible

```
frontend/
  app/
    layout.tsx           ← layout racine (navbar, QueryClientProvider)
    page.tsx             ← redirect vers /dashboard
    dashboard/
      page.tsx           ← TICKET-012
    top10/
      page.tsx           ← TICKET-013
    articles/
      page.tsx           ← TICKET-014
    ai-results/
      page.tsx           ← TICKET-015
  components/
    navbar.tsx
    status-badge.tsx     ← badge coloré pending/running/done/error
    confidence-bar.tsx   ← barre de progression 0-100
  lib/
    api.ts               ← client API typé
    types.ts             ← types TS miroir des schémas Pydantic
  package.json
  next.config.ts
  tailwind.config.ts
```

---

## Tâches

### 1. Initialisation

```bash
cd frontend
npx create-next-app@14 . --typescript --tailwind --app --no-src-dir
npx shadcn-ui@latest init
npx shadcn-ui@latest add button badge table card input select toast
npm install @tanstack/react-query axios
```

### 2. Types TypeScript (`frontend/lib/types.ts`)

```typescript
export interface Product {
  id: number
  source_product_id: string | null
  name: string
  brand: string | null
  showroom_price: number
  displayed_discount: number | null
  brand_price: number | null
  real_discount: number | null
  product_url: string | null
  is_interesting: boolean
  first_seen_at: string
  last_checked_at: string
  ai_status: 'pending' | 'running' | 'done' | 'error' | null
}

export interface ProductList {
  total: number
  page: number
  page_size: number
  items: Product[]
}

export type ScanStatus = 'idle' | 'running' | 'done' | 'error'

export interface ScanState {
  scan_id: string
  status: ScanStatus
  started_at: string | null
  finished_at: string | null
  products_found: number | null
  error: string | null
}

export interface CronState {
  active: boolean
  interval_seconds: number
  next_run_at: string | null
  last_run_at: string | null
}

export type AIJobStatus = 'pending' | 'running' | 'done' | 'error'

export interface AIJob {
  job_id: number
  product_id: number
  product_name: string
  provider: string
  status: AIJobStatus
  is_real_deal: boolean | null
  confidence: number | null
  real_market_price: number | null
  sources: string[]
  summary: string | null
  created_at: string
  finished_at: string | null
}
```

### 3. Client API (`frontend/lib/api.ts`)

```typescript
import axios from 'axios'
import type { Product, ProductList, ScanState, CronState, AIJob } from './types'

const http = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
})

export const api = {
  // Scan
  runScan: ()                          => http.post<{ status: string; scan_id: string }>('/scan/run'),
  getScanStatus: ()                    => http.get<ScanState>('/scan/status'),

  // Cron
  startCron: ()                        => http.post<CronState>('/cron/start'),
  stopCron: ()                         => http.post<{ status: string }>('/cron/stop'),
  getCronStatus: ()                    => http.get<CronState>('/cron/status'),

  // Produits
  getTop10: ()                         => http.get<Product[]>('/products/top10'),
  getProducts: (params: Record<string, unknown>) => http.get<ProductList>('/products', { params }),

  // IA
  launchResearch: (ids: number[])      => http.post('/ai/research', { product_ids: ids }),
  getAIJob: (jobId: number)            => http.get<AIJob>(`/ai/results/${jobId}`),
  getAIResults: (params: Record<string, unknown>) => http.get('/ai/results', { params }),
}
```

### 4. Layout racine (`frontend/app/layout.tsx`)

- `QueryClientProvider` wrappant tout le contenu
- `Navbar` avec liens : Dashboard · Top 10 · Articles · Résultats IA
- `Toaster` (shadcn) pour les notifications

### 5. Variable d'environnement

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Acceptance criteria

- [ ] `npm run dev` démarre sans erreur
- [ ] `npm run build` passe sans erreur TypeScript
- [ ] La navbar s'affiche sur toutes les pages
- [ ] `api.getScanStatus()` retourne la réponse typée sans erreur de compilation
- [ ] Les types TS couvrent tous les champs des schémas Pydantic
