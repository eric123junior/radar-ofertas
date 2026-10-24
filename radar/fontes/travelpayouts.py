"""Passagens aereas via Travelpayouts (dados do Aviasales).

Cadastro gratis em travelpayouts.com: o token da API e o "marker" (seu id de
afiliado) ficam em Perfil > Token da API. Duas consultas por execucao:

  get_special_offers   tarifas que a propria Aviasales marca como abaixo do normal
  prices_for_dates     o menor preco encontrado para cada destino a partir da origem

Para cada rota fica so a passagem mais barata. A "promocao" e medida contra a
mediana de preco daquela rota no historico do radar (ver __main__.selecionar);
as tarifas especiais entram como relampago mesmo antes de haver historico.
"""
from datetime import datetime, timedelta, timezone

from ..modelo import Oferta
from .base import Fonte

API = "https://api.travelpayouts.com"
SITE = "https://www.aviasales.com"


def _data(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def montar_link(caminho, marker):
    if not caminho:
        return ""
    url = caminho if caminho.startswith("http") else SITE + caminho
    if marker:
        url += ("&" if "?" in url else "?") + f"marker={marker}"
    return url


def converter(itens, cidades, marker, especial=False, agora=None):
    agora = agora or datetime.now(timezone.utc)
    ofertas = []
    for v in itens or []:
        preco = v.get("price") or v.get("value")
        origem, destino = v.get("origin"), v.get("destination")
        ida = _data(v.get("departure_at"))
        if not (preco and origem and destino and ida):
            continue
        if ida < agora + timedelta(days=2):
            continue
        volta = _data(v.get("return_at"))
        nome_o = cidades.get(origem, origem)
        nome_d = cidades.get(destino, destino)
        escalas = v.get("transfers")
        datas = ida.strftime("%d/%m/%Y") + (f" a {volta.strftime('%d/%m/%Y')}" if volta else "")
        tipo = "ida e volta" if volta else "só ida"
        link = montar_link(v.get("link", ""), marker)
        ofertas.append(Oferta(
            loja="aviasales",
            id_loja=f"{origem}-{destino}-{ida:%Y%m%d}-{volta:%Y%m%d}" if volta else f"{origem}-{destino}-{ida:%Y%m%d}",
            grupo=f"voo:{origem}-{destino}:{'iv' if volta else 'i'}",
            titulo=f"✈️ {nome_o} → {nome_d} ({tipo})",
            preco=float(preco),
            link=link,
            link_afiliado=link,
            afiliado=bool(marker),
            vendedor=v.get("airline", ""),
            relampago=especial,
            extras={
                "viagem": "voo",
                "datas": datas,
                "escalas": escalas,
                "cia": v.get("airline", ""),
                "destino": nome_d,
            },
        ))
    return ofertas


def mais_barata_por_rota(ofertas):
    melhor = {}
    for o in ofertas:
        atual = melhor.get(o.grupo)
        if atual is None or o.preco < atual.preco:
            if atual is not None and atual.relampago:
                o.relampago = True
            melhor[o.grupo] = o
        elif o.relampago:
            atual.relampago = True
    return list(melhor.values())


class Travelpayouts(Fonte):
    nome = "aviasales"
    por_feed = True  # nao usa PALAVRAS: busca todos os destinos a partir da origem

    def ativa(self):
        return bool(self.cfg.tp_token)

    def cidades(self):
        for idioma in ("pt", "en"):
            r = self._req("GET", f"{API}/data/{idioma}/cities.json", timeout=60)
            if r:
                return {c["code"]: (c.get("name") or c["code"]) for c in r.json() if c.get("code")}
        return {}

    def buscar_todas(self, palavras):
        c = self.cfg
        base = {"origin": c.origem, "currency": "brl", "token": c.tp_token}
        cidades = self.cidades()
        ofertas = []

        r = self._req("GET", f"{API}/aviasales/v3/get_special_offers", params={**base, "locale": "pt"})
        if r:
            ofertas += converter(r.json().get("data"), cidades, c.tp_marker, especial=True)

        r = self._req("GET", f"{API}/aviasales/v3/prices_for_dates", params={
            **base, "sorting": "price", "unique": "true", "one_way": "false", "limit": 200,
        })
        if r:
            ofertas += converter(r.json().get("data"), cidades, c.tp_marker)

        return mais_barata_por_rota(ofertas)
