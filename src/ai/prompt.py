from __future__ import annotations

from src.models import Product

SYSTEM_PROMPT = """Tu es un expert en analyse de prix e-commerce français.
On te donne les informations d'un produit vendu sur Showroomprivé.
Effectue une recherche pour déterminer si la remise est réelle.
Réponds UNIQUEMENT en JSON valide, sans markdown, avec exactement ces champs :
{
  "is_real_deal": <bool>,
  "confidence": <int 0-100>,
  "real_market_price": <float ou null>,
  "sources": [<url>, ...],
  "summary": "<2-3 phrases>"
}"""


def build_prompt(product: Product) -> str:
    return (
        f"Produit à analyser :\n"
        f"- Nom : {product.name}\n"
        f"- Marque : {product.brand or 'inconnue'}\n"
        f"- Prix Showroomprivé : {product.showroom_price} €\n"
        f"- Remise affichée : {product.displayed_discount or 'non renseignée'}%\n"
        f"- Prix de référence détecté : {product.brand_price or 'non disponible'} €\n"
        f"- URL produit : {product.product_url or 'non disponible'}\n\n"
        "Recherche le prix habituel de ce produit sur le web (historique 6 mois minimum), "
        "compare avec les prix actuels chez d'autres revendeurs (Amazon, FNAC, site officiel marque...), "
        "et détermine si la remise annoncée est réelle ou si le prix de référence est artificiel."
    )
