"""Conversao das respostas de cada API para Oferta (sem rede)."""
import hashlib
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.config import Config  # noqa: E402
from radar.fontes import amazon, mercadolivre, redes, shopee  # noqa: E402


class TestAmazon(unittest.TestCase):
    RESPOSTA = {"SearchResult": {"Items": [{
        "ASIN": "B0TESTE123",
        "DetailPageURL": "https://www.amazon.com.br/dp/B0TESTE123?tag=meutag-20",
        "ItemInfo": {"Title": {"DisplayValue": "Fone Bluetooth XYZ"}},
        "Images": {"Primary": {"Large": {"URL": "https://m.media-amazon.com/x.jpg"}}},
        "OffersV2": {"Listings": [{
            "Price": {"Money": {"Amount": 99.9}, "SavingBasis": {"Money": {"Amount": 249.9}}},
            "DealDetails": {"Badge": "Oferta Relâmpago", "EndTime": "2026-10-24T18:00:00Z",
                            "PercentClaimed": 85},
            "MerchantInfo": {"Name": "Amazon.com.br"},
        }]},
    }, {"ASIN": "SEMPRECO", "OffersV2": {"Listings": []}}]}}

    def test_converte_oferta_relampago(self):
        [o] = amazon.converter(self.RESPOSTA)
        self.assertEqual(o.chave, "amazon:B0TESTE123")
        self.assertEqual(o.desconto_pct, 60.0)
        self.assertTrue(o.relampago)
        self.assertEqual(o.estoque_restante_pct, 15)
        self.assertEqual(o.termina_em, datetime(2026, 10, 24, 18, tzinfo=timezone.utc))
        self.assertIn("tag=meutag-20", o.link_afiliado)

    def test_assinatura_sigv4_formato(self):
        h = amazon.assinar("AKID", "SEGREDO", "webservices.amazon.com.br", "us-east-1",
                           "SearchItems", "{}", datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
        self.assertEqual(h["x-amz-date"], "20260102T030405Z")
        self.assertTrue(h["Authorization"].startswith(
            "AWS4-HMAC-SHA256 Credential=AKID/20260102/us-east-1/ProductAdvertisingAPI/aws4_request, "
            "SignedHeaders=content-encoding;content-type;host;x-amz-date;x-amz-target, Signature="))


class TestMercadoLivre(unittest.TestCase):
    RESPOSTA = {"results": [{
        "id": "MLB123", "title": "Smartwatch ABC", "price": 150.0, "original_price": 300.0,
        "permalink": "https://produto.mercadolivre.com.br/MLB-123-smartwatch",
        "thumbnail": "http://http2.mlstatic.com/D_123-I.jpg",
        "tags": ["good_quality_thumbnail", "lightning_deal"],
        "seller": {"nickname": "LOJAOFICIAL"},
        "shipping": {"free_shipping": True},
    }]}

    def test_converte_com_matt_tool(self):
        cfg = Config(ml_matt_tool="12345", ml_matt_word="radar")
        [o] = mercadolivre.converter(self.RESPOSTA, cfg)
        self.assertEqual(o.desconto_pct, 50.0)
        self.assertTrue(o.relampago)
        self.assertTrue(o.imagem.endswith("-O.jpg"))
        self.assertEqual(o.link_afiliado,
                         "https://produto.mercadolivre.com.br/MLB-123-smartwatch?matt_tool=12345&matt_word=radar")

    def test_modelo_de_link_tem_prioridade(self):
        cfg = Config(ml_link_afiliado="https://ir.to/?u={url}", ml_matt_tool="1")
        link = mercadolivre.link_afiliado("https://x.com/a?b=1", cfg)
        self.assertEqual(link, "https://ir.to/?u=https%3A%2F%2Fx.com%2Fa%3Fb%3D1")


class TestShopee(unittest.TestCase):
    def test_converte_e_calcula_preco_original(self):
        resp = {"data": {"productOfferV2": {"nodes": [{
            "itemId": 987, "productName": "Air Fryer 4L", "price": "199.00", "priceMin": "180.00",
            "priceDiscountRate": 40, "sales": 2300, "ratingStar": "4.8",
            "imageUrl": "https://cf.shopee.com.br/x", "offerLink": "https://s.shopee.com.br/abc",
            "productLink": "https://shopee.com.br/p/987", "shopName": "Loja Oficial",
        }]}}}
        [o] = shopee.converter(resp)
        self.assertEqual(o.preco, 180.0)
        self.assertEqual(o.preco_original, 300.0)
        self.assertEqual(o.link_afiliado, "https://s.shopee.com.br/abc")
        self.assertEqual(o.avaliacao, 4.8)

    def test_assinatura(self):
        h = shopee.cabecalho("APP", "SEG", '{"q":1}', ts=1700000000)
        esperado = hashlib.sha256(b'APP1700000000{"q":1}SEG').hexdigest()
        self.assertEqual(h["Authorization"],
                         f"SHA256 Credential=APP, Timestamp=1700000000, Signature={esperado}")


class TestRedes(unittest.TestCase):
    def test_lomadee(self):
        resp = {"offers": [{"id": 1, "name": "Monitor 27", "price": 800, "priceFrom": 1600,
                            "link": "https://redir.lomadee.com/x", "thumbnail": "t.jpg",
                            "store": {"name": "Magalu"}}]}
        [o] = redes.converter_lomadee(resp)
        self.assertEqual(o.desconto_pct, 50.0)
        self.assertEqual(o.vendedor, "Magalu")

    def test_awin_filtra_por_palavra(self):
        csv = ("aw_product_id,product_name,search_price,rrp_price,aw_deep_link,merchant_name\n"
               "1,SSD NVMe 1TB,299.90,599.90,https://awin1.com/a,Loja X\n"
               "2,Cadeira gamer,500,900,https://awin1.com/b,Loja X\n")
        ofertas = redes.converter_awin(csv, ["ssd"])
        self.assertEqual([o.id_loja for o in ofertas], ["1"])
        self.assertEqual(ofertas[0].link_afiliado, "https://awin1.com/a")


if __name__ == "__main__":
    unittest.main()
