"""Passagens: conversao da Travelpayouts, preco normal da rota e selecao."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.__main__ import selecionar  # noqa: E402
from radar.banco import Banco  # noqa: E402
from radar.canais.telegram import montar_legenda  # noqa: E402
from radar.config import Config  # noqa: E402
from radar.fontes import travelpayouts as tp  # noqa: E402
from radar.pontuacao import avaliar  # noqa: E402

AGORA = datetime.now(timezone.utc)
IDA = (AGORA + timedelta(days=40)).strftime("%Y-%m-%dT10:00:00-03:00")
VOLTA = (AGORA + timedelta(days=50)).strftime("%Y-%m-%dT22:00:00-03:00")
CIDADES = {"SAO": "São Paulo", "LIS": "Lisboa", "REC": "Recife"}


def voo(destino="LIS", preco=2400, **kw):
    d = {"origin": "SAO", "destination": destino, "price": preco, "airline": "TP",
         "departure_at": IDA, "return_at": VOLTA, "transfers": 0,
         "link": f"/search/SAO0101{destino}10011?t=TP"}
    d.update(kw)
    return d


class TestConversao(unittest.TestCase):
    def test_converte_voo(self):
        [o] = tp.converter([voo()], CIDADES, "123456", especial=True)
        self.assertEqual(o.titulo, "✈️ São Paulo → Lisboa (ida e volta)")
        self.assertEqual(o.grupo, "voo:SAO-LIS:iv")
        self.assertTrue(o.relampago and o.viagem and o.afiliado)
        self.assertEqual(o.link_afiliado, "https://www.aviasales.com/search/SAO0101LIS10011?t=TP&marker=123456")
        self.assertEqual(o.extras["escalas"], 0)

    def test_sem_marker_nao_e_afiliado(self):
        [o] = tp.converter([voo()], CIDADES, "")
        self.assertFalse(o.afiliado)
        self.assertNotIn("marker", o.link_afiliado)

    def test_descarta_partida_muito_proxima_e_incompleta(self):
        amanha = (AGORA + timedelta(hours=20)).isoformat()
        self.assertEqual(tp.converter([voo(departure_at=amanha), voo(price=None)], CIDADES, ""), [])

    def test_fica_a_mais_barata_por_rota_e_mantem_selo(self):
        especial = tp.converter([voo(preco=2600)], CIDADES, "", especial=True)
        comum = tp.converter([voo(preco=2400), voo("REC", 500)], CIDADES, "")
        rotas = {o.grupo: o for o in tp.mais_barata_por_rota(especial + comum)}
        self.assertEqual(rotas["voo:SAO-LIS:iv"].preco, 2400)
        self.assertTrue(rotas["voo:SAO-LIS:iv"].relampago)
        self.assertFalse(rotas["voo:SAO-REC:iv"].relampago)


class TestSelecaoViagem(unittest.TestCase):
    def setUp(self):
        self.banco = Banco(":memory:")
        self.cfg = Config()

    def _historico(self, grupo, precos):
        for i, p in enumerate(precos):
            self.banco.registrar_preco(grupo, p, AGORA - timedelta(days=i + 1))

    def test_mediana(self):
        self._historico("g", [10, 30, 20, 40])
        self.assertEqual(self.banco.mediana("g", antes_de=AGORA), (25, 4))

    def test_tarifa_especial_passa_sem_historico(self):
        ofertas = tp.converter([voo()], CIDADES, "", especial=True)
        [(o, av)] = selecionar(self.cfg, self.banco, ofertas)
        self.assertIn("tarifa promocional", av.motivos)

    def test_preco_comum_sem_historico_nao_passa(self):
        self.assertEqual(selecionar(self.cfg, self.banco, tp.converter([voo()], CIDADES, "")), [])

    def test_abaixo_da_mediana_da_rota_passa(self):
        self._historico("voo:SAO-LIS:iv", [4000, 4200, 3800, 4100, 3900])
        [(o, av)] = selecionar(self.cfg, self.banco, tp.converter([voo(preco=2400)], CIDADES, ""))
        self.assertEqual(o.preco_original, 4000)
        self.assertEqual(o.desconto_pct, 40.0)
        self.assertIn("menor preço já registrado", av.motivos)

    def test_nao_repete_a_rota_em_outra_data(self):
        self._historico("voo:SAO-LIS:iv", [4000] * 5)
        [(o, av)] = selecionar(self.cfg, self.banco, tp.converter([voo(preco=2400)], CIDADES, ""))
        self.banco.marcar_enviada(o.chave_historico, o.preco, av.nota)
        outra = voo(preco=2380, departure_at=(AGORA + timedelta(days=60)).isoformat())
        self.assertEqual(selecionar(self.cfg, self.banco, tp.converter([outra], CIDADES, "")), [])

    def test_legenda(self):
        [o] = tp.converter([voo()], CIDADES, "1", especial=True)
        o.preco_original = 4000.0
        txt = montar_legenda(o, avaliar(o))
        self.assertIn("PASSAGEM EM PROMOÇÃO", txt)
        self.assertIn("voo direto · TP", txt)
        self.assertIn("Normalmente <s>R$ 4.000,00</s>", txt)
        self.assertIn("Link de afiliado", txt)


if __name__ == "__main__":
    unittest.main()
