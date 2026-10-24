"""Diagnostico da Travelpayouts: o que o token consegue consultar.

Imprime status e o comeco de cada resposta (nunca o token), mais quantas
passagens o radar converteria. Serve para ajustar o conversor ao formato real.

Uso: python ferramentas/sondar_tp.py   (ou o workflow "Diagnostico")
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.config import Config  # noqa: E402
from radar.fontes import travelpayouts as tp  # noqa: E402

API = tp.API


def mostrar(nome, r):
    print(f"[{r.status_code}] {nome}\n      {r.text[:500]}\n")


def main():
    cfg = Config.do_ambiente()
    if not cfg.tp_token:
        print("sem TP_TOKEN")
        return 1
    fonte = tp.Travelpayouts(cfg)
    get = lambda caminho, **p: fonte.http.get(API + caminho, params={**p, "token": cfg.tp_token}, timeout=60)  # noqa: E731
    print(f"origem: {cfg.origem} | marker: {'sim' if cfg.tp_marker else 'nao'}\n")

    cidades = fonte.cidades()
    print(f"cidades carregadas: {len(cidades)} (ex.: SAO={cidades.get('SAO')}, LIS={cidades.get('LIS')})\n")

    r = get("/aviasales/v3/get_special_offers", origin=cfg.origem, currency="brl", locale="pt")
    mostrar("tarifas especiais /aviasales/v3/get_special_offers", r)
    if r.ok:
        print("      convertidas:", len(tp.converter(r.json().get("data"), cidades, cfg.tp_marker, True)), "\n")

    r = get("/aviasales/v3/prices_for_dates", origin=cfg.origem, currency="brl", sorting="price",
            unique="true", one_way="false", limit=200)
    mostrar("menores precos por destino /aviasales/v3/prices_for_dates", r)
    if r.ok:
        conv = tp.converter(r.json().get("data"), cidades, cfg.tp_marker)
        print("      convertidas:", len(conv))
        for o in sorted(conv, key=lambda o: o.preco)[:5]:
            print(f"        R$ {o.preco:>8.0f}  {o.titulo}  {o.extras['datas']}  escalas={o.extras['escalas']}")
        print()

    r = get("/aviasales/v3/grouped_prices", origin=cfg.origem, destination="LIS", currency="brl",
            group_by="departure_at")
    mostrar("precos por mes SAO-LIS /aviasales/v3/grouped_prices", r)

    # hoteis: a API do Hotellook pode ter sido descontinuada; so verificamos se responde
    r = fonte.http.get("https://engine.hotellook.com/api/v2/cache.json", timeout=30, params={
        "location": "Rio de Janeiro", "currency": "brl", "limit": 3, "token": cfg.tp_token})
    mostrar("hoteis (Hotellook) /api/v2/cache.json", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
