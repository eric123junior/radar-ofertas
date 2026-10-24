"""Mercado Livre via API oficial de busca (sites/MLB/search).

A busca exige um token de aplicativo. Basta criar um app gratis em
developers.mercadolivre.com.br (nao e o programa de afiliados) e configurar
ML_CLIENT_ID e ML_CLIENT_SECRET: o token de 6h e gerado a cada execucao.
ML_ACCESS_TOKEN continua aceito para quem preferir gerar o token na mao.

O link de afiliado nao vem da API: ele e montado com o modelo configurado em
ML_LINK_AFILIADO (ex.: um gerador de links seu) ou com os parametros
matt_tool/matt_word do programa de afiliados. Sem nenhum dos dois, o link vai
direto para o produto.
"""
from urllib.parse import quote, urlencode

from ..modelo import Oferta
from .base import Fonte, log

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
        venda = it.get("sale_price") or {}
        original = it.get("original_price") or venda.get("regular_amount")
        tags = set(it.get("tags") or [])
        promo = set(((venda.get("metadata") or {}).get("campaign_type") or "").split(","))
        url = it.get("permalink", "")
        img = (it.get("thumbnail") or "").replace("-I.jpg", "-O.jpg").replace("http://", "https://")
        ofertas.append(Oferta(
            loja="mercadolivre",
            id_loja=it.get("id", ""),
            titulo=it.get("title", ""),
            preco=float(preco),
            preco_original=float(original) if original else None,
            link=url,
            link_afiliado=link_afiliado(url, cfg),
            afiliado=link_afiliado(url, cfg) != url,
            imagem=img,
            vendedor=((it.get("seller") or {}).get("nickname")) or "",
            vendidos=it.get("sold_quantity"),
            relampago=bool((tags | promo) & TAGS_RELAMPAGO),
            extras={"frete_gratis": bool((it.get("shipping") or {}).get("free_shipping"))},
        ))
    return ofertas


class MercadoLivre(Fonte):
    nome = "mercadolivre"

    def __init__(self, cfg):
        super().__init__(cfg)
        self._token = cfg.ml_access_token

    def ativa(self):
        c = self.cfg
        return bool(c.ml_access_token or (c.ml_client_id and c.ml_client_secret))

    def token(self):
        if self._token:
            return self._token
        r = self._req("POST", "https://api.mercadolibre.com/oauth/token", data={
            "grant_type": "client_credentials",
            "client_id": self.cfg.ml_client_id,
            "client_secret": self.cfg.ml_client_secret,
        })
        if r:
            self._token = r.json().get("access_token", "")
        if not self._token:
            log.warning("mercadolivre: nao foi possivel gerar o token; confira ML_CLIENT_ID e ML_CLIENT_SECRET")
            self._token = None  # evita tentar de novo a cada palavra
        return self._token

    def buscar(self, palavra):
        tk = self.token() if self._token is not None else None
        if not tk:
            return []
        params = {"q": palavra, "limit": 50, "discount": "30-100"}
        r = self._req("GET", "https://api.mercadolibre.com/sites/MLB/search", params=params,
                      headers={"Authorization": f"Bearer {tk}"})
        return converter(r.json(), self.cfg) if r else []
