# TICKET-015 — Page Résultats IA

**Epic:** Frontend  
**Priorité:** P2  
**Complexité:** S  
**Dépendances:** TICKET-011, TICKET-010

---

## Contexte

Historique de toutes les analyses IA effectuées. Permet de voir les verdicts passés, de comprendre les sources utilisées, et de relancer une analyse expirée.

---

## Maquette fonctionnelle

```
Résultats IA                                         Total : 87 analyses

Statut [Tous ▾]   Provider [Tous ▾]

Produit                Provider   Statut      Confiance  Verdict        Date
────────────────────────────────────────────────────────────────────────────────
Sac cuir Milano        claude     ✓ Terminé   ████░ 82%  ✓ Vrai deal    25/04 10h01
Montre Automatic       openai     ✗ Erreur    —          —              25/04 10h02
Veste cuir homme       gemini     ⟳ En cours  —          —              25/04 10h03

                        ← 1  2  3 →
```

### Panel de détail (drawer)

Clic sur une ligne → drawer droit avec :

```
Sac cuir Milano — Analyse Claude                        [✕]
────────────────────────────────────────────────────────
Verdict      ✓ Vrai deal
Confiance    ████████░░  82%
Prix marché  ~240 €
Provider     claude (claude-opus-4-7)

Résumé
Le prix habituel de ce sac est autour de 230-250€ sur Amazon et
le site officiel. La remise de 64% est confirmée par 3 sources.
Le prix de référence Showroomprivé semble exact.

Sources (3)
• amazon.fr — Longchamp Milano cuir — 239 €
• longchamp.com/fr — Sac Milano — 250 €
• idealo.fr — Comparateur — 230-260 €

[↻ Relancer l'analyse]
```

---

## Implémentation

### Polling

- `GET /ai/results` toutes les **30 secondes**
- Quand des jobs `pending` ou `running` sont présents : toutes les **3 secondes**

```typescript
const hasPendingJobs = data?.items.some(j => ['pending', 'running'].includes(j.status))

const { data } = useQuery({
  queryKey: ['ai-results', filters],
  queryFn: ...,
  refetchInterval: hasPendingJobs ? 3000 : 30000,
})
```

### Relancer une analyse

```typescript
const relaunch = async (productId: number) => {
  // Forcer le rechargement même si TTL non expiré :
  // appeler directement POST /ai/research — le backend gère le TTL
  await api.launchResearch([productId])
  queryClient.invalidateQueries({ queryKey: ['ai-results'] })
}
```

### Composants

- `ConfidenceBar` : réutilisé depuis TICKET-013
- `StatusBadge` : réutilisé depuis TICKET-012
- `SourceList` : liste de liens cliquables (ouvre `target="_blank" rel="noopener"`)

---

## Acceptance criteria

- [ ] La liste se rafraîchit automatiquement et accélère son polling si des jobs sont actifs
- [ ] Le drawer s'ouvre et se ferme sans perdre la position de scroll dans la liste
- [ ] Les sources sont des liens cliquables vers les URLs externes
- [ ] "Relancer l'analyse" crée un nouveau job et le nouveau statut apparaît en temps réel
- [ ] Filtre par statut et provider fonctionne côté API (params passés à `GET /ai/results`)
- [ ] Un job en `error` affiche le message d'erreur dans le drawer (champ `summary` ou `raw_response` tronqué)
