"""Contrato comum das fontes de ofertas.

Cada fonte separa a chamada de rede (`buscar`) da conversao do JSON
(`converter`). A conversao e uma funcao pura, testada com respostas reais
salvas em tests/fixtures, sem precisar de credenciais.
"""
import logging
import time

import requests

log = logging.getLogger("radar")
UA = "RadarOfertas/1.0 (+https://github.com/eric123junior/radar-ofertas)"


class Fonte:
    nome = "base"

    def __init__(self, cfg):
        self.cfg = cfg
        self.http = requests.Session()
        self.http.headers["User-Agent"] = UA

    def ativa(self) -> bool:
        raise NotImplementedError

    def buscar(self, palavra: str) -> list:
        raise NotImplementedError

    def _req(self, metodo, url, tentativas=3, **kw):
        kw.setdefault("timeout", 30)
        for i in range(1, tentativas + 1):
            try:
                r = self.http.request(metodo, url, **kw)
                if r.status_code == 429 or r.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                if r.status_code >= 400:
                    # erro do lado de quem chama (credencial, parametro): nao adianta repetir
                    log.warning("%s: HTTP %d em %s: %s", self.nome, r.status_code,
                                url.split("?")[0], r.text[:300])
                    return None
                return r
            except requests.RequestException as e:
                if i == tentativas:
                    log.warning("%s: falhou %s %s (%s)", self.nome, metodo, url.split("?")[0], e)
                    return None
                time.sleep(1.5 * i)
