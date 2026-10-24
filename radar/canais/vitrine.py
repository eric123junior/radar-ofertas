"""Gera site/ofertas.json, lido pela vitrine estatica em site/index.html.

Mantem as ofertas aprovadas das ultimas 48h, mais recentes e melhores primeiro,
e descarta as que ja passaram do horario de termino.
"""
import json
import os
from datetime import datetime, timedelta, timezone

LIMITE = 120
JANELA_HORAS = 48


def atualizar(pasta, novas):
    """`novas` e uma lista de (oferta, avaliacao)."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "ofertas.json")
    agora = datetime.now(timezone.utc)
    atuais = []
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            atuais = json.load(f).get("ofertas", [])

    por_chave = {o["chave"]: o for o in atuais}
    for oferta, av in novas:
        d = oferta.para_json()
        d.update(nota=av.nota, motivos=av.motivos, publicada_em=agora.isoformat())
        d.pop("extras", None)
        por_chave[d["chave"]] = d

    corte = (agora - timedelta(hours=JANELA_HORAS)).isoformat()
    vivas = [
        o for o in por_chave.values()
        if o["publicada_em"] >= corte and (not o.get("termina_em") or o["termina_em"] > agora.isoformat())
    ]
    vivas.sort(key=lambda o: (o["publicada_em"][:13], o["nota"]), reverse=True)

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump({"atualizado_em": agora.isoformat(), "ofertas": vivas[:LIMITE]},
                  f, ensure_ascii=False, indent=1)
    return caminho
