# Flux de listing produits Showroomprivé

## Ce qui est listé sur la home

- La home publique liste des **ventes** (`/vente.aspx?vente=<saleId>`), pas des produits.
- Exemple: `https://www.showroomprive.com/vente.aspx?vente=152412`

## Résolution vers le catalogue produit

- `tousproduits.aspx?vente=<saleId>` redirige vers `/catalog/sale/<saleId>`.
- `categorie.aspx?categorie=<categoryId>` redirige vers `/catalog/sale/category/<categoryId>`.

## Pages de listing produits

- Listing principal de la vente: `/catalog/sale/<saleId>`.
- Listing catégorie: `/catalog/sale/category/<categoryId>`.
- Pagination via query string: `?page=2`, `?page=3`, etc.

## DOM utile pour le scraper

- Carte produit: `.js-product-card`.
- ID produit: `data-product-id` (souvent présent à plusieurs endroits dans la carte).
- Lien produit: `a.hit-product[href*="ficheproduitp.aspx?produit="]`.
- Prix courant: bloc `.hit-prices` (valeur en euros dans un élément `.fw-bold ...`).
- Remise affichée: badge avec `%` dans `.hit-prices`.

## Implication pour le code

1. Entrer par la home / URL configurée.
2. Découvrir les `saleId` via les liens de ventes.
3. Mapper chaque `saleId` vers `/catalog/sale/<saleId>`.
4. Parcourir les pages `?page=N`.
5. Parser `.js-product-card` et dédupliquer par `source_product_id`.
