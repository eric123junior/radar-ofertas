"""Gera site/ofertas.json, lido pela vitrine estatica em site/index.html.

Mantem as ofertas aprovadas das ultimas 48h, mais recentes e melhores primeiro,
e descarta as que ja passaram do horario de termino. Opcionalmente escreve a
mesma lista em Markdown (OFERTAS.md), legivel direto no GitHub.
"""
import json
import os
from datetime import datetime, timedelta, timezone

LIMITE = 120
JANELA_HORAS = 48


def atualizar(pasta, novas, md=None):
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
        x = d.pop("extras", None) or {}
        for k in ("viagem", "datas", "escalas"):
            if k in x:
                d[k] = x[k]
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
    if md:
        escrever_markdown(md, vivas[:LIMITE], agora)
    return caminho


def _reais(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def escrever_markdown(caminho, ofertas, agora):
    hora = agora.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    linhas = [
        "# Ofertas do radar", "",
        f"Atualizado em {hora} (horário de Brasília). Ofertas das últimas {JANELA_HORAS}h, "
        "melhores primeiro. Preço e estoque mudam a qualquer momento.", "",
    ]
    if not ofertas:
        linhas.append("_Nenhuma oferta passou no filtro ainda._")
    else:
        linhas += ["| Nota | Desconto | Preço | Produto | Loja | Por quê |",
                   "|---:|---:|---:|---|---|---|"]
        for o in ofertas:
            titulo = o["titulo"][:90].replace("|", "/").replace("[", "(").replace("]", ")")
            de = f" ~~{_reais(o['preco_original'])}~~" if o.get("preco_original") else ""
            if o.get("datas"):
                titulo += f" ({o['datas']})"
            motivos = ", ".join(m for m in o.get("motivos", []) if not m.endswith("% off"))
            linhas.append(
                f"| {o['nota']:.0f} | -{o['desconto_pct']:.0f}% | **{_reais(o['preco'])}**{de} "
                f"| [{titulo}]({o['link_afiliado']}) | {o.get('vendedor') or o['loja']} | {motivos} |")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
