# TICKET-014 — Page Articles (liste complète + filtres)

**Epic:** Frontend  
**Priorité:** P2  
**Complexité:** M  
**Dépendances:** TICKET-011, TICKET-004, TICKET-010

---

## Contexte

Vue exhaustive de tous les produits en base. Permet de fouiller l'historique, filtrer par marque, prix, remise, et lancer des analyses IA sur des articles spécifiques.

---

## Maquette fonctionnelle

```
Articles                                             Total : 342 produits

┌─ Filtres ──────────────────────────────────────────────────────────┐
│ Marque [___________] Remise min [__]% Prix max [___]€              │
│ ☐ Offres intéressantes uniquement     Tri [Remise réelle ▾] [↓]   │
└────────────────────────────────────────────────────────────────────┘

☐  Produit                  Marque     Showroom  Remise   IA        Actions
──────────────────────────────────────────────────────────────────────────────
☐  Sac cuir Milano          Longchamp   89 €     64.4%    ✓ 82%    [🔍 Analyser]
☐  Montre Automatic         Tissot     149 €     60.0%    —        [🔍 Analyser]

                        ← 1  2  3  ...  7 →                 50/page ▾
[Analyser la sélection (0)]
```

---

## Implémentation

### Filtres avec URL params

Les filtres sont synchronisés avec les query params de l'URL (pour permettre le partage de liens filtrés) :

```typescript
// next/navigation
const router = useRouter()
const searchParams = useSearchParams()

// Lecture
const brand = searchParams.get('brand') ?? ''
const minDiscount = Number(searchParams.get('min_discount') ?? 0)

// Écriture (debounce 300ms sur les champs texte)
const updateFilter = (key: string, value: string) => {
  const params = new URLSearchParams(searchParams)
  if (value) params.set(key, value)
  else params.delete(key)
  router.push(`?${params.toString()}`)
}
```

### Pagination

```typescript
const { data, isLoading } = useQuery({
  queryKey: ['products', { page, brand, minDiscount, maxPrice, interestingOnly, sort, order }],
  queryFn: () => api.getProducts({ page, page_size: 50, brand, min_discount: minDiscount, ... }).then(r => r.data),
  placeholderData: keepPreviousData,  // évite le flash lors du changement de page
})
```

### Actions par ligne

- **[Analyser]** → `POST /ai/research` avec le `product_id` de la ligne → badge IA mis à jour
- Clic sur le nom du produit → ouvre l'URL Showroomprivé dans un nouvel onglet

### Ligne expandable (optionnel)

Clic sur une ligne → affiche une ligne de détail avec `first_seen_at`, `last_checked_at`, `source_product_id`, lien URL produit.

---

## Acceptance criteria

- [ ] Les filtres sont appliqués côté API (pas côté client)
- [ ] Les filtres sont persistés dans l'URL
- [ ] La pagination affiche le nombre total et permet la navigation
- [ ] `keepPreviousData` évite le flash lors du changement de page ou de filtre
- [ ] Sélection multiple + "Analyser la sélection" fonctionne (max 10 rappelé dans le bouton si dépassé)
- [ ] Un tableau vide (aucun résultat) affiche un message explicite, pas un composant cassé
