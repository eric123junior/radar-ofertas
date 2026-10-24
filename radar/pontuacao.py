"""Nota de 0 a 100 para decidir o que e oportunidade de verdade.

A ideia e priorizar oferta relampago: desconto alto, que acaba logo, com pouco
estoque e preco abaixo do que ja vimos. Cada sinal soma pontos:

    desconto        ate 40 pts  (40% de desconto = 20 pts, 80% = 40 pts)
    menor preco     ate 20 pts  (abaixo do menor preco do historico)
    urgencia        ate 20 pts  (relampago, acaba em poucas horas)
    escassez        ate 10 pts  (estoque restante baixo)
    confianca       ate 10 pts  (avaliacao e volume de vendas)

Ofertas com desconto "de mentira" (preco atual acima do menor do historico por
mais de 10%) perdem pontos.
"""
from dataclasses import dataclass

from .modelo import Oferta


@dataclass
class Avaliacao:
    nota: float
    motivos: list
    menor_historico: float | None = None


def avaliar(oferta: Oferta, menor_historico=None, agora=None) -> Avaliacao:
    pts = 0.0
    motivos = []

    d = oferta.desconto_pct
    pts += min(d, 80) / 2
    if d:
        motivos.append(f"{d:.0f}% off")

    if menor_historico:
        if oferta.preco < menor_historico * 0.99:
            pts += 20
            motivos.append("menor preço já registrado")
        elif oferta.preco <= menor_historico * 1.01:
            pts += 10
            motivos.append("igual ao menor preço")
        elif oferta.preco > menor_historico * 1.10:
            pts -= 15
            motivos.append("acima do menor preço histórico")

    urg = 0.0
    if oferta.relampago:
        urg += 10
        motivos.append("oferta relâmpago")
    mins = oferta.minutos_restantes(agora)
    if mins is not None and mins > 0:
        if mins <= 60:
            urg += 10
            motivos.append("acaba em menos de 1h")
        elif mins <= 6 * 60:
            urg += 6
            motivos.append(f"acaba em {mins / 60:.0f}h")
        elif mins <= 24 * 60:
            urg += 3
    pts += min(urg, 20)

    est = oferta.estoque_restante_pct
    if est is not None:
        if est <= 20:
            pts += 10
            motivos.append(f"só {est:.0f}% do estoque")
        elif est <= 50:
            pts += 5

    conf = 0.0
    if oferta.avaliacao is not None:
        if oferta.avaliacao >= 4.5:
            conf += 6
        elif oferta.avaliacao >= 4.0:
            conf += 3
        elif oferta.avaliacao < 3.5:
            conf -= 5
    if oferta.vendidos:
        if oferta.vendidos >= 1000:
            conf += 4
        elif oferta.vendidos >= 100:
            conf += 2
    pts += min(conf, 10)

    if oferta.cupom:
        motivos.append(f"cupom {oferta.cupom}")

    return Avaliacao(nota=round(max(0.0, min(pts, 100.0)), 1), motivos=motivos,
                     menor_historico=menor_historico)
