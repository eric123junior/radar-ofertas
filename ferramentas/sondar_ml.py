"""Diagnostico: quais endpoints da API do Mercado Livre o app consegue usar.

O ML libera ou bloqueia endpoints por politica de cada aplicativo. Este script
gera o token com ML_CLIENT_ID/ML_CLIENT_SECRET e testa os caminhos que o radar
pode usar, imprimindo so o status e o comeco da resposta (nunca o token).

Uso: python ferramentas/sondar_ml.py   (ou o workflow "Diagnostico")
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.config import Config  # noqa: E402
from radar.fontes.mercadolivre import MercadoLivre  # noqa: E402

API = "https://api.mercadolibre.com"


def mostrar(nome, r):
    corpo = r.text[:350].replace("\n", " ")
    print(f"[{r.status_code}] {nome}\n      {corpo}\n")


def main():
    cfg = Config.do_ambiente()
    ml = MercadoLivre(cfg)
    tk = ml.token()
    if not tk:
        print("sem token: confira ML_CLIENT_ID e ML_CLIENT_SECRET")
        return 1
    print("token gerado\n")
    h = {"Authorization": f"Bearer {tk}"}
    get = lambda caminho, **p: ml.http.get(API + caminho, headers=h, params=p, timeout=30)  # noqa: E731

    mostrar("busca de anuncios /sites/MLB/search", get("/sites/MLB/search", q="fone bluetooth", limit=2))

    r = get("/products/search", status="active", site_id="MLB", q="fone bluetooth", limit=3)
    mostrar("catalogo /products/search", r)
    produto = None
    if r.ok:
        res = r.json().get("results") or []
        produto = res[0]["id"] if res else None

    if produto:
        r = get(f"/products/{produto}")
        mostrar(f"produto /products/{produto}", r)
        if r.ok:
            print("      buy_box_winner:", json.dumps(r.json().get("buy_box_winner"))[:300], "\n")
        r = get(f"/products/{produto}/items", limit=3)
        mostrar(f"anuncios do produto /products/{produto}/items", r)
        item = None
        if r.ok:
            res = r.json().get("results") or []
            item = res[0].get("item_id") if res else None
        if item:
            mostrar(f"anuncio /items/{item}", get(f"/items/{item}"))
            mostrar("multiget /items?ids=", get("/items", ids=item, attributes="id,price,original_price,title"))

    r = get("/highlights/MLB/category/MLB1051")
    mostrar("mais vendidos /highlights/MLB/category/MLB1051 (celulares)", r)

    mostrar("tendencias /trends/MLB", get("/trends/MLB"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
