# TICKET-013 — Page Top 10

**Epic:** Frontend  
**Priorité:** P1  
**Complexité:** S  
**Dépendances:** TICKET-011, TICKET-004, TICKET-010

---

## Contexte

Vue principale pour l'utilisateur final : les 10 meilleures affaires du dernier scan, avec la possibilité de lancer une vérification IA sur un ou plusieurs articles.

---

## Maquette fonctionnelle

```
Top 10 — Meilleures remises réelles          [↻ Actualiser]

☐  #  Produit                Marque    Showroom  Marque   Remise  IA
──────────────────────────────────────────────────────────────────────
☐  1  Sac cuir Milano        Longchamp  89 €     250 €    64.4%   ✓ Confirmé
☐  2  Montre Automatic       Tissot    149 €     420 €    64.5%   — Non analysé
☐  3  Veste cuir homme       Hugo Boss  99 €     280 €    64.6%   ⟳ En cours
...

[Analyser la sélection (2)]          [Analyser tout le top 10]
```

---

## Implémentation

### Polling

- `GET /products/top10` toutes les **60 secondes** (données changent à chaque scan)
- Quand des jobs IA sont `pending` ou `running` parmi les produits listés, requêter `GET /ai/results/{job_id}` toutes les **3 secondes** (polling par job ID)

### Sélection + actions

```typescript
const [selected, setSelected] = useState<Set<number>>(new Set())

const handleAnalyze = async (ids: number[]) => {
  const { data } = await api.launchResearch(ids)
  // Stocker les job_ids retournés pour lancer le polling
  setActiveJobs(prev => [...prev, ...data.jobs])
  toast.success(`${ids.length} analyse(s) IA lancée(s)`)
}
```

### Colonne IA

| Valeur `ai_status` | Affichage |
|---|---|
| `null` | "— Non analysé" (gris) |
| `pending` | spinner + "En attente" |
| `running` | spinner + "En cours" |
| `done` + `is_real_deal: true` | ✓ badge vert "Confirmé" + confidence% |
| `done` + `is_real_deal: false` | ✗ badge rouge "Inflation prix" + confidence% |
| `error` | ⚠ badge orange "Erreur" |

Cliquer sur un badge IA ouvre un panel latéral (sheet shadcn) avec le détail : summary, sources, prix marché réel, provider utilisé.

### Composant `ConfidenceBar`

```tsx
<ConfidenceBar value={82} />
// → barre verte de 82% de largeur avec "82%" affiché
```

---

## Acceptance criteria

- [ ] Le top 10 se rafraîchit automatiquement toutes les 60s
- [ ] La sélection multiple fonctionne (checkbox ligne + header)
- [ ] "Analyser la sélection" est désactivé si aucune sélection
- [ ] Le badge IA se met à jour en temps réel pendant l'analyse
- [ ] Le panel latéral affiche sources cliquables (liens externes)
- [ ] Un produit sans `real_discount` (brand_price non disponible) est exclu du top 10 côté API — vérifier que l'UI gère un tableau vide
