"""Configuracao lida de variaveis de ambiente (ou de um arquivo .env local).

Nenhuma chave fica no codigo. No GitHub Actions elas vem de Settings > Secrets.
Uma loja sem credencial simplesmente fica desligada.
"""
import os
from dataclasses import dataclass, field

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def carregar_dotenv(caminho=None):
    caminho = caminho or os.path.join(RAIZ, ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _lista(nome, padrao=""):
    return [x.strip() for x in os.environ.get(nome, padrao).split(",") if x.strip()]


def _float(nome, padrao):
    v = os.environ.get(nome)
    return float(v) if v else padrao


@dataclass
class Config:
    # o que procurar
    palavras: list = field(default_factory=list)
    # criterio de "oferta boa": desconto minimo e nota minima (0-100)
    desconto_minimo: float = 40.0
    nota_minima: float = 60.0
    preco_maximo: float | None = None
    max_por_execucao: int = 10
    # nao repetir a mesma oferta antes de N horas (a nao ser que o preco caia de novo)
    horas_sem_repetir: float = 24.0

    # Amazon PA-API 5
    amazon_access_key: str = ""
    amazon_secret_key: str = ""
    amazon_tag: str = ""
    amazon_host: str = "webservices.amazon.com.br"
    amazon_region: str = "us-east-1"

    # Mercado Livre
    ml_access_token: str = ""
    ml_client_id: str = ""       # app gratis em developers.mercadolivre.com.br
    ml_client_secret: str = ""
    ml_link_afiliado: str = ""   # modelo com {url}, ex.: https://seu-gerador/?u={url}
    ml_matt_tool: str = ""       # parametros do programa de afiliados do ML
    ml_matt_word: str = ""

    # Shopee Afiliados
    shopee_app_id: str = ""
    shopee_secret: str = ""

    # Lomadee (Magalu, Americanas, etc.)
    lomadee_app_token: str = ""
    lomadee_source_id: str = ""

    # Awin: URLs de feed de produtos (CSV) geradas no painel Awin, separadas por virgula
    awin_feeds: list = field(default_factory=list)

    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # arquivos de saida
    banco: str = os.path.join(RAIZ, "estado", "radar.db")
    pasta_site: str = os.path.join(RAIZ, "site")

    @classmethod
    def do_ambiente(cls):
        carregar_dotenv()
        e = os.environ.get
        pm = e("PRECO_MAXIMO")
        return cls(
            palavras=_lista("PALAVRAS", "fone bluetooth,smartwatch,air fryer,ssd,monitor"),
            desconto_minimo=_float("DESCONTO_MINIMO", 40.0),
            nota_minima=_float("NOTA_MINIMA", 60.0),
            preco_maximo=float(pm) if pm else None,
            max_por_execucao=int(e("MAX_POR_EXECUCAO", "10")),
            horas_sem_repetir=_float("HORAS_SEM_REPETIR", 24.0),
            amazon_access_key=e("AMAZON_ACCESS_KEY", ""),
            amazon_secret_key=e("AMAZON_SECRET_KEY", ""),
            amazon_tag=e("AMAZON_TAG", ""),
            amazon_host=e("AMAZON_HOST", "webservices.amazon.com.br"),
            amazon_region=e("AMAZON_REGION", "us-east-1"),
            ml_access_token=e("ML_ACCESS_TOKEN", ""),
            ml_client_id=e("ML_CLIENT_ID", ""),
            ml_client_secret=e("ML_CLIENT_SECRET", ""),
            ml_link_afiliado=e("ML_LINK_AFILIADO", ""),
            ml_matt_tool=e("ML_MATT_TOOL", ""),
            ml_matt_word=e("ML_MATT_WORD", ""),
            shopee_app_id=e("SHOPEE_APP_ID", ""),
            shopee_secret=e("SHOPEE_SECRET", ""),
            lomadee_app_token=e("LOMADEE_APP_TOKEN", ""),
            lomadee_source_id=e("LOMADEE_SOURCE_ID", ""),
            awin_feeds=_lista("AWIN_FEEDS"),
            telegram_token=e("TELEGRAM_TOKEN", ""),
            telegram_chat_id=e("TELEGRAM_CHAT_ID", ""),
            banco=e("RADAR_BANCO", cls.banco),
            pasta_site=e("RADAR_SITE", cls.pasta_site),
        )
