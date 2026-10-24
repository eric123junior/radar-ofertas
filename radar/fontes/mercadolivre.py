"""Mercado Livre via API oficial de busca (sites/MLB/search).

A busca exige um access token de aplicativo (developers.mercadolivre.com.br).
O link de afiliado nao vem da API: ele e montado com o modelo configurado em
ML_LINK_AFILIADO (ex.: um gerador de links seu) ou com os parametros
matt_tool/matt_word do programa de afiliados.
"""
from urllib.parse import quote, urlencode

from ..modelo import Oferta
from .base import Fonte

TAGS_RELAMPAGO = {"lightning_deal", "deal_of_the_day", "today_promotion"}


def link_afiliado(url, cfg):
    if not url:
        return ""
    if cfg.ml_link_afiliado:
        return cfg.ml_link_afiliado.replace("{url}", quote(url, safe=""))
    if cfg.ml_matt_tool:
        params = {"matt_tool": cfg.ml_matt_tool}
        if cfg.ml_matt_word:
            params["matt_word"] = cfg.ml_matt_word
        sep = "&" if "?" in url else "?"
        return url + sep + urlencode(params)
    return url


def converter(resposta: dict, cfg) -> list:
    ofertas = []
    for it in resposta.get("results") or []:
        preco = it.get("price")
        if preco is None:
            continue
        tags = set(it.get("tags") or [])
        promo = set((it.get("sale_price") or {}).get("metadata", {}).get("campaign_type", "").split(","))
        url = it.get("permalink", "")
        img = (it.get("thumbnail") or "").replace("-I.jpg", "-O.jpg")
        ofertas.append(Oferta(
            loja="mercadolivre",
            id_loja=it.get("id", ""),
            titulo=it.get("title", ""),
            preco=float(preco),
            preco_original=float(it["original_price"]) if it.get("original_price") else None,
            link=url,
            link_afiliado=link_afiliado(url, cfg),
            imagem=img,
            vendedor=((it.get("seller") or {}).get("nickname")) or "",
            vendidos=it.get("sold_quantity"),
            relampago=bool((tags | promo) & TAGS_RELAMPAGO),
            extras={"frete_gratis": bool((it.get("shipping") or {}).get("free_shipping"))},
        ))
    return ofertas


class MercadoLivre(Fonte):
    nome = "mercadolivre"

    def ativa(self):
        return bool(self.cfg.ml_access_token)

    def buscar(self, palavra):
        params = {"q": palavra, "limit": 50, "discount": "30-100"}
        r = self._req("GET", "https://api.mercadolibre.com/sites/MLB/search", params=params,
                      headers={"Authorization": f"Bearer {self.cfg.ml_access_token}"})
        return converter(r.json(), self.cfg) if r else []
