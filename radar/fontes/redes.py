"""Redes de afiliados com varias lojas: Lomadee e Awin.

Lomadee: API de ofertas (Magalu, Americanas, Casas Bahia...). O `link` ja vem
rastreado com o seu sourceId.

Awin: nao tem busca por palavra; cada anunciante aprovado gera um feed de
produtos (CSV, as vezes .gz) no painel. O radar baixa o feed e filtra pelas
palavras configuradas. O `aw_deep_link` ja e o link de afiliado.
"""
import csv
import gzip
import io

from ..modelo import Oferta
from .base import Fonte


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def converter_lomadee(resposta: dict) -> list:
    ofertas = []
    for o in resposta.get("offers") or []:
        preco = _num(o.get("price"))
        if preco is None:
            continue
        original = _num(o.get("priceFrom"))
        if not original and _num(o.get("discount")):
            original = preco + _num(o.get("discount"))
        loja = (o.get("store") or {}).get("name", "")
        ofertas.append(Oferta(
            loja="lomadee",
            id_loja=str(o.get("id", "")),
            titulo=o.get("name", ""),
            preco=preco,
            preco_original=original,
            link=o.get("link", ""),
            link_afiliado=o.get("link", ""),
            imagem=o.get("thumbnail", ""),
            vendedor=loja,
            extras={"loja_parceira": loja},
        ))
    return ofertas


def converter_awin(texto: str, palavras: list) -> list:
    termos = [p.lower() for p in palavras]
    ofertas = []
    for row in csv.DictReader(io.StringIO(texto)):
        nome = row.get("product_name", "")
        if termos and not any(t in nome.lower() for t in termos):
            continue
        preco = _num(row.get("search_price"))
        if preco is None:
            continue
        original = _num(row.get("rrp_price")) or _num(row.get("product_price_old"))
        loja = row.get("merchant_name", "")
        ofertas.append(Oferta(
            loja="awin",
            id_loja=row.get("aw_product_id", ""),
            titulo=nome,
            preco=preco,
            preco_original=original,
            link=row.get("merchant_deep_link", ""),
            link_afiliado=row.get("aw_deep_link", ""),
            imagem=row.get("merchant_image_url") or row.get("aw_image_url", ""),
            vendedor=loja,
            extras={"loja_parceira": loja},
        ))
    return ofertas


class Lomadee(Fonte):
    nome = "lomadee"

    def ativa(self):
        return bool(self.cfg.lomadee_app_token and self.cfg.lomadee_source_id)

    def buscar(self, palavra):
        url = f"https://api.lomadee.com/v3/{self.cfg.lomadee_app_token}/offer/_search"
        r = self._req("GET", url, params={"sourceId": self.cfg.lomadee_source_id,
                                          "keyword": palavra, "size": 50, "sort": "discount"})
        return converter_lomadee(r.json()) if r else []


class Awin(Fonte):
    """O feed traz todos os produtos; baixa uma vez e filtra todas as palavras."""
    nome = "awin"
    por_feed = True

    def ativa(self):
        return bool(self.cfg.awin_feeds)

    def buscar_todas(self, palavras):
        ofertas = []
        for url in self.cfg.awin_feeds:
            r = self._req("GET", url, timeout=120)
            if not r:
                continue
            bruto = r.content
            if bruto[:2] == b"\x1f\x8b":
                bruto = gzip.decompress(bruto)
            ofertas += converter_awin(bruto.decode("utf-8", "replace"), palavras)
        return ofertas
