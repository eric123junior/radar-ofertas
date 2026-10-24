"""Amazon Associados via Product Advertising API 5 (SearchItems).

Usa os recursos OffersV2, que trazem `DealDetails` com o selo da oferta
("Oferta Relampago", "Oferta por tempo limitado"), o horario de termino e o
percentual ja resgatado. O DetailPageURL devolvido ja vem com a sua tag.

A assinatura e AWS SigV4, implementada aqui para nao depender de SDK.
Obs.: a PA-API so libera chamadas depois que a conta de associado tem vendas
qualificadas nos ultimos 30 dias.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone

from ..modelo import Oferta
from .base import Fonte

RECURSOS = [
    "ItemInfo.Title",
    "Images.Primary.Large",
    "OffersV2.Listings.Price",
    "OffersV2.Listings.DealDetails",
    "OffersV2.Listings.MerchantInfo",
    "CustomerReviews.StarRating",
]


def _hmac(chave, msg):
    return hmac.new(chave, msg.encode("utf-8"), hashlib.sha256).digest()


def assinar(access_key, secret_key, host, region, alvo, corpo, agora=None):
    """Devolve os headers SigV4 para uma chamada PA-API 5."""
    agora = agora or datetime.now(timezone.utc)
    amz_date = agora.strftime("%Y%m%dT%H%M%SZ")
    data = agora.strftime("%Y%m%d")
    servico = "ProductAdvertisingAPI"
    caminho = "/paapi5/" + alvo.lower()
    headers = {
        "content-encoding": "amz-1.0",
        "content-type": "application/json; charset=utf-8",
        "host": host,
        "x-amz-date": amz_date,
        "x-amz-target": f"com.amazon.paapi5.v1.ProductAdvertisingAPIv1.{alvo}",
    }
    nomes = sorted(headers)
    canonico = "\n".join([
        "POST", caminho, "",
        "".join(f"{k}:{headers[k]}\n" for k in nomes),
        ";".join(nomes),
        hashlib.sha256(corpo.encode("utf-8")).hexdigest(),
    ])
    escopo = f"{data}/{region}/{servico}/aws4_request"
    a_assinar = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, escopo,
        hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
    ])
    k = _hmac(("AWS4" + secret_key).encode("utf-8"), data)
    k = _hmac(k, region)
    k = _hmac(k, servico)
    k = _hmac(k, "aws4_request")
    assinatura = hmac.new(k, a_assinar.encode("utf-8"), hashlib.sha256).hexdigest()
    headers["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{escopo}, "
        f"SignedHeaders={';'.join(nomes)}, Signature={assinatura}"
    )
    return headers


def _data(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def converter(resposta: dict) -> list:
    ofertas = []
    itens = (resposta.get("SearchResult") or {}).get("Items") or []
    for it in itens:
        listings = ((it.get("OffersV2") or {}).get("Listings")) or []
        if not listings:
            continue
        lst = listings[0]
        preco_info = lst.get("Price") or {}
        preco = (preco_info.get("Money") or {}).get("Amount")
        if preco is None:
            continue
        original = ((preco_info.get("SavingBasis") or {}).get("Money") or {}).get("Amount")
        deal = lst.get("DealDetails") or {}
        selo = (deal.get("Badge") or "").lower()
        resgatado = deal.get("PercentClaimed")
        titulo = (((it.get("ItemInfo") or {}).get("Title") or {}).get("DisplayValue")) or ""
        img = ((((it.get("Images") or {}).get("Primary") or {}).get("Large")) or {}).get("URL", "")
        estrelas = (((it.get("CustomerReviews") or {}).get("StarRating")) or {}).get("Value")
        url = it.get("DetailPageURL", "")
        ofertas.append(Oferta(
            loja="amazon",
            id_loja=it.get("ASIN", ""),
            titulo=titulo,
            preco=float(preco),
            preco_original=float(original) if original else None,
            link=url,
            link_afiliado=url,
            imagem=img,
            vendedor=((lst.get("MerchantInfo") or {}).get("Name")) or "Amazon",
            avaliacao=float(estrelas) if estrelas else None,
            relampago=bool(deal) and ("relâmpago" in selo or "lightning" in selo
                                      or "tempo limitado" in selo or "limited" in selo),
            termina_em=_data(deal.get("EndTime")),
            estoque_restante_pct=(100 - float(resgatado)) if resgatado is not None else None,
            extras={"selo": deal.get("Badge", "")},
        ))
    return ofertas


class Amazon(Fonte):
    nome = "amazon"

    def ativa(self):
        c = self.cfg
        return bool(c.amazon_access_key and c.amazon_secret_key and c.amazon_tag)

    def buscar(self, palavra):
        c = self.cfg
        corpo = json.dumps({
            "Keywords": palavra,
            "PartnerTag": c.amazon_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.com.br",
            "ItemCount": 10,
            "MinSavingPercent": int(max(c.desconto_minimo - 10, 10)),
            "Resources": RECURSOS,
        })
        headers = assinar(c.amazon_access_key, c.amazon_secret_key,
                          c.amazon_host, c.amazon_region, "SearchItems", corpo)
        r = self._req("POST", f"https://{c.amazon_host}/paapi5/searchitems",
                      data=corpo.encode("utf-8"), headers=headers)
        return converter(r.json()) if r else []
