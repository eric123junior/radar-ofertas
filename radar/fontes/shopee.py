"""Shopee Afiliados via Open API GraphQL (productOfferV2).

A propria API devolve o `offerLink` ja rastreado com a sua conta de afiliado.
Autenticacao: SHA256(appId + timestamp + corpo + secret) no header.
"""
import hashlib
import json
import time

from ..modelo import Oferta
from .base import Fonte, log

URL = "https://open-api.affiliate.shopee.com.br/graphql"

CONSULTA = """
query Ofertas($kw: String, $page: Int, $limit: Int) {
  productOfferV2(keyword: $kw, sortType: 2, page: $page, limit: $limit) {
    nodes {
      itemId productName price priceMin priceMax priceDiscountRate
      sales ratingStar imageUrl offerLink productLink shopName
    }
  }
}
"""


def cabecalho(app_id, secret, corpo, ts=None):
    ts = ts or int(time.time())
    assinatura = hashlib.sha256(f"{app_id}{ts}{corpo}{secret}".encode("utf-8")).hexdigest()
    return {
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={assinatura}",
        "Content-Type": "application/json",
    }


def converter(resposta: dict) -> list:
    nodes = (((resposta.get("data") or {}).get("productOfferV2")) or {}).get("nodes") or []
    ofertas = []
    for n in nodes:
        try:
            preco = float(n.get("priceMin") or n.get("price"))
        except (TypeError, ValueError):
            continue
        taxa = n.get("priceDiscountRate") or 0
        original = round(preco / (1 - taxa / 100), 2) if 0 < taxa < 100 else None
        estrelas = n.get("ratingStar")
        ofertas.append(Oferta(
            loja="shopee",
            id_loja=str(n.get("itemId", "")),
            titulo=n.get("productName", ""),
            preco=preco,
            preco_original=original,
            link=n.get("productLink", ""),
            link_afiliado=n.get("offerLink") or n.get("productLink", ""),
            imagem=n.get("imageUrl", ""),
            vendedor=n.get("shopName", ""),
            avaliacao=float(estrelas) if estrelas else None,
            vendidos=n.get("sales"),
        ))
    return ofertas


class Shopee(Fonte):
    nome = "shopee"

    def ativa(self):
        return bool(self.cfg.shopee_app_id and self.cfg.shopee_secret)

    def buscar(self, palavra):
        corpo = json.dumps({"query": CONSULTA,
                            "variables": {"kw": palavra, "page": 1, "limit": 50}},
                           separators=(",", ":"))
        r = self._req("POST", URL, data=corpo.encode("utf-8"),
                      headers=cabecalho(self.cfg.shopee_app_id, self.cfg.shopee_secret, corpo))
        if not r:
            return []
        dados = r.json()
        if dados.get("errors"):
            log.warning("shopee: %s", dados["errors"][0].get("message", dados["errors"]))
            return []
        return converter(dados)
