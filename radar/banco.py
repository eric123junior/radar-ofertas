"""SQLite com historico de precos e registro do que ja foi enviado.

O historico serve para duas coisas: detectar "menor preco ja visto" (sinal forte
de oferta real, nao de preco inflado para parecer desconto) e evitar mandar a
mesma oferta duas vezes no canal.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

ESQUEMA = """
CREATE TABLE IF NOT EXISTS historico_preco (
    chave     TEXT NOT NULL,
    preco     REAL NOT NULL,
    visto_em  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_hist_chave ON historico_preco (chave, visto_em);

CREATE TABLE IF NOT EXISTS enviados (
    chave       TEXT NOT NULL,
    preco       REAL NOT NULL,
    nota        REAL NOT NULL,
    enviado_em  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_env_chave ON enviados (chave, enviado_em);
"""


def _agora():
    return datetime.now(timezone.utc)


class Banco:
    def __init__(self, caminho):
        if caminho != ":memory:":
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
        self.con = sqlite3.connect(caminho)
        self.con.executescript(ESQUEMA)

    def fechar(self):
        self.con.commit()
        self.con.close()

    def registrar_preco(self, chave, preco, quando=None):
        quando = quando or _agora()
        self.con.execute(
            "INSERT INTO historico_preco (chave, preco, visto_em) VALUES (?, ?, ?)",
            (chave, preco, quando.isoformat()),
        )

    def menor_preco(self, chave, dias=90, antes_de=None):
        """Menor preco visto nos ultimos `dias`, sem contar a coleta atual."""
        antes_de = antes_de or _agora()
        desde = (antes_de - timedelta(days=dias)).isoformat()
        row = self.con.execute(
            "SELECT MIN(preco), COUNT(*) FROM historico_preco "
            "WHERE chave = ? AND visto_em >= ? AND visto_em < ?",
            (chave, desde, antes_de.isoformat()),
        ).fetchone()
        menor, n = row
        return (menor, n) if n else (None, 0)

    def mediana(self, chave, dias=60, antes_de=None):
        """Mediana dos precos vistos nos ultimos `dias` (o "preco normal")."""
        antes_de = antes_de or _agora()
        desde = (antes_de - timedelta(days=dias)).isoformat()
        precos = [p for (p,) in self.con.execute(
            "SELECT preco FROM historico_preco WHERE chave = ? AND visto_em >= ? AND visto_em < ? "
            "ORDER BY preco", (chave, desde, antes_de.isoformat()))]
        n = len(precos)
        if not n:
            return None, 0
        meio = n // 2
        med = precos[meio] if n % 2 else (precos[meio - 1] + precos[meio]) / 2
        return med, n

    def ja_enviada(self, chave, preco, horas):
        """True se a oferta saiu nas ultimas `horas` e o preco nao caiu desde entao.

        Uma queda de 3% ou mais conta como oferta nova e pode ser reenviada.
        """
        desde = (_agora() - timedelta(hours=horas)).isoformat()
        row = self.con.execute(
            "SELECT MIN(preco) FROM enviados WHERE chave = ? AND enviado_em >= ?",
            (chave, desde),
        ).fetchone()
        ultimo = row[0]
        if ultimo is None:
            return False
        return preco > ultimo * 0.97

    def marcar_enviada(self, chave, preco, nota):
        self.con.execute(
            "INSERT INTO enviados (chave, preco, nota, enviado_em) VALUES (?, ?, ?, ?)",
            (chave, preco, nota, _agora().isoformat()),
        )
        self.con.commit()
