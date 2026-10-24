"""Ponto de entrada: python -m radar [--teste] [--palavras "a,b"]

Fluxo de uma execucao:
  1. busca em todas as lojas com credencial configurada
  2. registra precos no historico e calcula a nota de cada oferta
  3. filtra (desconto minimo, nota minima, preco maximo, ja enviada)
  4. envia as melhores para o Telegram e atualiza a vitrine

--teste mostra o que seria enviado, sem mandar nada e sem gravar no banco
(o historico existente e usado para calcular o preco normal).
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from .banco import Banco
from .canais import vitrine
from .canais.telegram import Telegram, reais
from .config import Config
from .fontes import TODAS
from .pontuacao import avaliar

log = logging.getLogger("radar")


def coletar(cfg, fontes):
    ofertas = {}
    for f in fontes:
        if getattr(f, "por_feed", False):
            achadas = f.buscar_todas(cfg.palavras)
        else:
            achadas = []
            for p in cfg.palavras:
                achadas += f.buscar(p)
        log.info("%-13s %4d ofertas", f.nome, len(achadas))
        for o in achadas:
            if o.link_afiliado and o.titulo:
                ofertas[o.chave] = o
    return list(ofertas.values())


def selecionar(cfg, banco, ofertas, gravar=True):
    agora = datetime.now(timezone.utc)
    aprovadas = []
    for o in ofertas:
        hist = o.chave_historico
        menor, _ = banco.menor_preco(hist, antes_de=agora)
        if o.viagem and o.preco_original is None:
            # sem "preco de" na API: o normal da rota e a mediana do historico
            mediana, n = banco.mediana(hist, antes_de=agora)
            if n >= 5:
                o.preco_original = mediana
        if gravar:
            banco.registrar_preco(hist, o.preco, agora)
        if o.viagem:
            sem_historico = o.preco_original is None
            if o.desconto_pct < cfg.desconto_minimo_viagem and not (o.relampago and sem_historico):
                continue
        elif o.desconto_pct < cfg.desconto_minimo:
            continue
        if cfg.preco_maximo and o.preco > cfg.preco_maximo and not o.viagem:
            continue
        mins = o.minutos_restantes(agora)
        if mins is not None and mins <= 5:
            continue
        av = avaliar(o, menor, agora)
        if av.nota < (cfg.nota_minima_viagem if o.viagem else cfg.nota_minima):
            continue
        if banco.ja_enviada(hist, o.preco, cfg.horas_sem_repetir):
            continue
        aprovadas.append((o, av))
    banco.con.commit()
    aprovadas.sort(key=lambda par: par[1].nota, reverse=True)
    return aprovadas[: cfg.max_por_execucao]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="radar")
    ap.add_argument("--teste", action="store_true", help="nao envia nem grava nada")
    ap.add_argument("--palavras", help="sobrescreve PALAVRAS, separadas por virgula")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    cfg = Config.do_ambiente()
    if args.palavras:
        cfg.palavras = [p.strip() for p in args.palavras.split(",") if p.strip()]

    fontes = [F(cfg) for F in TODAS]
    fontes = [f for f in fontes if f.ativa()]
    if bool(cfg.ml_client_id) != bool(cfg.ml_client_secret) and not cfg.ml_access_token:
        falta = "ML_CLIENT_SECRET" if cfg.ml_client_id else "ML_CLIENT_ID"
        log.warning("mercadolivre: falta o secret %s; o Mercado Livre fica desligado", falta)
    if not fontes:
        # sai com sucesso para o agendamento nao disparar alerta antes da configuracao
        log.warning("nenhuma loja configurada; preencha o .env ou os secrets (veja .env.example)")
        return 0
    log.info("lojas ativas: %s", ", ".join(f.nome for f in fontes))

    # no modo teste o historico e lido normalmente, mas nada e gravado
    banco = Banco(cfg.banco)
    ofertas = coletar(cfg, fontes)
    escolhidas = selecionar(cfg, banco, ofertas, gravar=not args.teste)
    log.info("%d de %d ofertas passaram no filtro", len(escolhidas), len(ofertas))

    if args.teste:
        for o, av in escolhidas:
            print(f"[{av.nota:5.1f}] {o.loja:12} {reais(o.preco):>13}  -{o.desconto_pct:.0f}%  "
                  f"{o.titulo[:70]}\n        {', '.join(av.motivos)}\n        {o.link_afiliado}")
        return 0

    tg = Telegram(cfg)
    enviadas = []
    for o, av in escolhidas:
        if tg.ativo() and not tg.enviar(o, av):
            continue
        banco.marcar_enviada(o.chave_historico, o.preco, av.nota)
        enviadas.append((o, av))
    # sem novidade nao regrava (evita um commit vazio a cada execucao);
    # ofertas encerradas tambem somem pela propria vitrine no navegador
    md = os.path.join(os.path.dirname(cfg.pasta_site), "OFERTAS.md")
    if enviadas or not os.path.exists(md):
        vitrine.atualizar(cfg.pasta_site, enviadas, md=md)
    log.info("%d ofertas publicadas%s", len(enviadas), "" if tg.ativo() else " (só na vitrine)")
    banco.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
