# TICKET-012 — Page Dashboard (contrôle scan + cron)

**Epic:** Frontend  
**Priorité:** P1  
**Complexité:** S  
**Dépendances:** TICKET-011, TICKET-002, TICKET-003

---

## Contexte

Page d'accueil de l'application. Permet de voir l'état global du système et d'agir dessus sans ligne de commande.

---

## Maquette fonctionnelle

```
┌─────────────────────────────────────────────────────┐
│  Showroom Deals Agent                               │
├──────────────────────┬──────────────────────────────┤
│  SCAN                │  CRON                        │
│  ────────────────    │  ─────────────────────       │
│  Statut: idle ●      │  Statut: actif ●             │
│  Dernier: il y a 2h  │  Intervalle: 60 min          │
│  Produits trouvés: 47│  Prochain run: dans 43 min   │
│                      │                              │
│  [▶ Lancer un scan]  │  [■ Stopper] [▶ Démarrer]   │
├──────────────────────┴──────────────────────────────┤
│  Dernière activité                                  │
│  ─────────────────                                  │
│  • 10:03 — Scan terminé, 47 produits                │
│  • 09:01 — Scan terminé, 52 produits                │
│  • 08:00 — Cron démarré                             │
└─────────────────────────────────────────────────────┘
```

---

## Implémentation

### Polling

- `GET /scan/status` toutes les **2 secondes** quand `status === "running"`, toutes les 30 secondes sinon
- `GET /cron/status` toutes les **30 secondes**

```typescript
// Avec TanStack Query
const { data: scanState } = useQuery({
  queryKey: ['scan-status'],
  queryFn: () => api.getScanStatus().then(r => r.data),
  refetchInterval: (data) => data?.status === 'running' ? 2000 : 30000,
})
```

### Actions

- **Lancer un scan** → `POST /scan/run` → toast "Scan lancé" → polling passe à 2s
- **Démarrer cron** → `POST /cron/start` → toast "Cron démarré"
- **Stopper cron** → `POST /cron/stop` → confirmation dialog avant action

### États visuels du bouton scan

| Status | Bouton | Couleur badge |
|---|---|---|
| `idle` | "Lancer un scan" (actif) | gris |
| `running` | "Scan en cours…" (désactivé + spinner) | orange |
| `done` | "Lancer un scan" (actif) | vert |
| `error` | "Lancer un scan" (actif) | rouge |

### Composants à créer

```typescript
// StatusBadge : réutilisé dans plusieurs pages
<StatusBadge status="running" /> // → badge orange "En cours"
<StatusBadge status="done" />    // → badge vert "Terminé"
```

---

## Acceptance criteria

- [ ] Le statut scan se met à jour en temps réel pendant un scan
- [ ] Le bouton "Lancer un scan" est grisé pendant un scan en cours
- [ ] "Stopper le cron" affiche un dialog de confirmation
- [ ] Les toasts confirment chaque action (succès et erreur)
- [ ] Un erreur 409 (scan déjà en cours) affiche un message clair, pas un crash
- [ ] La page fonctionne sans scan ni cron actif (état initial vide)
