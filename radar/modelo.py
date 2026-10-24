"""Estrutura unica de oferta, comum a todas as lojas.

Cada fonte converte a resposta da sua API para `Oferta`; daqui para frente o
resto do sistema (pontuacao, banco, canais) nao sabe de onde a oferta veio.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Oferta:
    loja: str                 # "amazon", "mercadolivre", "shopee", "lomadee", "awin"
    id_loja: str              # id do produto na loja (ASIN, MLB..., itemId)
    titulo: str
    preco: float              # preco atual em reais
    preco_original: float | None = None
    link: str = ""            # link do produto, sem afiliacao
    link_afiliado: str = ""   # link final que vai para o canal
    afiliado: bool = True     # False quando o link ainda vai direto para a loja
    imagem: str = ""
    vendedor: str = ""
    avaliacao: float | None = None   # 0 a 5
    vendidos: int | None = None
    relampago: bool = False          # a loja marcou como oferta relampago/do dia
    termina_em: datetime | None = None
    estoque_restante_pct: float | None = None  # 0 a 100, quando a loja informa
    cupom: str = ""
    extras: dict = field(default_factory=dict)

    @property
    def chave(self) -> str:
        return f"{self.loja}:{self.id_loja}"

    @property
    def desconto_pct(self) -> float:
        if not self.preco_original or self.preco_original <= self.preco:
            return 0.0
        return round((1 - self.preco / self.preco_original) * 100, 1)

    def minutos_restantes(self, agora: datetime | None = None) -> float | None:
        if not self.termina_em:
            return None
        agora = agora or datetime.now(timezone.utc)
        return (self.termina_em - agora).total_seconds() / 60

    def para_json(self) -> dict:
        d = asdict(self)
        d["termina_em"] = self.termina_em.isoformat() if self.termina_em else None
        d["desconto_pct"] = self.desconto_pct
        d["chave"] = self.chave
        return d
