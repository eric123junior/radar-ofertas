"""Pontuacao, historico, anti-repeticao, legenda e vitrine."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.__main__ import selecionar  # noqa: E402
from radar.banco import Banco  # noqa: E402
from radar.canais import vitrine  # noqa: E402
from radar.canais.telegram import montar_legenda, reais  # noqa: E402
from radar.config import Config  # noqa: E402
from radar.modelo import Oferta  # noqa: E402
from radar.pontuacao import avaliar  # noqa: E402

AGORA = datetime.now(timezone.utc)


def oferta(**kw):
    base = dict(loja="amazon", id_loja="A1", titulo="Produto", preco=100.0,
                preco_original=200.0, link_afiliado="https://a/1")
    base.update(kw)
    return Oferta(**base)


class TestPontuacao(unittest.TestCase):
    def test_relampago_vale_mais_que_desconto_comum(self):
        comum = avaliar(oferta(), agora=AGORA)
        relampago = avaliar(oferta(relampago=True, termina_em=AGORA + timedelta(minutes=40),
                                   estoque_restante_pct=10), agora=AGORA)
        self.assertEqual(comum.nota, 25.0)
        self.assertEqual(relampago.nota, 25 + 20 + 10)
        self.assertIn("acaba em menos de 1h", relampago.motivos)

    def test_desconto_falso_perde_pontos(self):
        # "50% off" mas ja vimos por 70: o preco "original" foi inflado
        av = avaliar(oferta(), menor_historico=70.0, agora=AGORA)
        self.assertEqual(av.nota, 10.0)
        self.assertIn("acima do menor preço histórico", av.motivos)

    def test_menor_preco_historico_soma(self):
        av = avaliar(oferta(), menor_historico=130.0, agora=AGORA)
        self.assertEqual(av.nota, 45.0)


class TestSelecao(unittest.TestCase):
    def setUp(self):
        self.banco = Banco(":memory:")
        self.cfg = Config(desconto_minimo=40, nota_minima=40, max_por_execucao=5)

    def test_filtra_ordena_e_nao_repete(self):
        boa = oferta(id_loja="BOA", relampago=True, termina_em=AGORA + timedelta(hours=2))
        fraca = oferta(id_loja="FRACA", preco=150.0)          # 25% off
        acabando = oferta(id_loja="FIM", relampago=True, termina_em=AGORA + timedelta(minutes=3))
        escolhidas = selecionar(self.cfg, self.banco, [fraca, boa, acabando])
        self.assertEqual([o.id_loja for o, _ in escolhidas], ["BOA"])

        self.banco.marcar_enviada(boa.chave, boa.preco, escolhidas[0][1].nota)
        self.assertEqual(selecionar(self.cfg, self.banco, [boa]), [])

        # caiu mais 10%: vira oferta nova
        mais_barata = oferta(id_loja="BOA", preco=90.0, relampago=True,
                             termina_em=AGORA + timedelta(hours=2))
        self.assertEqual(len(selecionar(self.cfg, self.banco, [mais_barata])), 1)

    def test_historico_ignora_coleta_atual(self):
        self.banco.registrar_preco("amazon:A1", 80.0, AGORA - timedelta(days=2))
        self.assertEqual(self.banco.menor_preco("amazon:A1", antes_de=AGORA), (80.0, 1))
        self.assertEqual(self.banco.menor_preco("amazon:A1", antes_de=AGORA - timedelta(days=3)), (None, 0))


class TestCanais(unittest.TestCase):
    def test_reais(self):
        self.assertEqual(reais(1234.5), "R$ 1.234,50")

    def test_legenda_escapa_html_e_avisa_afiliado(self):
        o = oferta(titulo="Fone <Pro> & cia", relampago=True, cupom="RADAR10")
        txt = montar_legenda(o, avaliar(o))
        self.assertIn("Fone &lt;Pro&gt; &amp; cia", txt)
        self.assertIn("OFERTA RELÂMPAGO", txt)
        self.assertIn("<s>R$ 200,00</s>", txt)
        self.assertIn("RADAR10", txt)
        self.assertIn("Link de afiliado", txt)

    def test_vitrine_remove_encerradas(self):
        with tempfile.TemporaryDirectory() as d:
            viva = oferta(id_loja="VIVA")
            morta = oferta(id_loja="MORTA", termina_em=AGORA - timedelta(minutes=1))
            vitrine.atualizar(d, [(viva, avaliar(viva)), (morta, avaliar(morta))])
            with open(os.path.join(d, "ofertas.json"), encoding="utf-8") as f:
                dados = json.load(f)
            self.assertEqual([o["chave"] for o in dados["ofertas"]], ["amazon:VIVA"])


if __name__ == "__main__":
    unittest.main()
