"""Publica ofertas num canal ou grupo do Telegram via Bot API.

Crie o bot com o @BotFather, adicione-o como administrador do canal e use o
@nome_do_canal (ou o id numerico) em TELEGRAM_CHAT_ID.
"""
import html
import logging

import requests

log = logging.getLogger("radar")

NOMES_LOJA = {
    "amazon": "Amazon",
    "mercadolivre": "Mercado Livre",
    "shopee": "Shopee",
    "lomadee": "Lomadee",
    "awin": "Awin",
}


def reais(v):
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def montar_legenda(oferta, avaliacao):
    e = html.escape
    loja = oferta.extras.get("loja_parceira") or NOMES_LOJA.get(oferta.loja, oferta.loja)
    linhas = []
    if oferta.relampago or (oferta.minutos_restantes() or 1e9) <= 360:
        linhas.append("⚡ <b>OFERTA RELÂMPAGO</b> ⚡")
    linhas.append(f"<b>{e(oferta.titulo[:180])}</b>")
    linhas.append("")
    if oferta.preco_original:
        linhas.append(f"De <s>{reais(oferta.preco_original)}</s>")
    linhas.append(f"🔥 Por <b>{reais(oferta.preco)}</b>"
                  + (f"  (-{oferta.desconto_pct:.0f}%)" if oferta.desconto_pct else ""))
    if oferta.cupom:
        linhas.append(f"🎟️ Cupom: <code>{e(oferta.cupom)}</code>")
    destaques = [m for m in avaliacao.motivos if not m.endswith("% off")]
    if destaques:
        linhas.append("✅ " + " · ".join(e(m) for m in destaques[:3]))
    linhas.append(f"🏬 {e(loja)}")
    linhas.append("")
    linhas.append("⏳ Preço e estoque podem mudar a qualquer momento.")
    if oferta.afiliado:
        linhas.append("<i>Link de afiliado: posso receber comissão, sem custo extra para você.</i>")
    return "\n".join(linhas)


class Telegram:
    def __init__(self, cfg):
        self.token = cfg.telegram_token
        self.chat = cfg.telegram_chat_id

    def ativo(self):
        return bool(self.token and self.chat)

    def enviar(self, oferta, avaliacao) -> bool:
        legenda = montar_legenda(oferta, avaliacao)
        teclado = {"inline_keyboard": [[{"text": "🛒 Ver oferta", "url": oferta.link_afiliado}]]}
        base = f"https://api.telegram.org/bot{self.token}"
        if oferta.imagem:
            metodo, dados = "sendPhoto", {"photo": oferta.imagem, "caption": legenda}
        else:
            metodo, dados = "sendMessage", {"text": legenda}
        dados.update(chat_id=self.chat, parse_mode="HTML", reply_markup=teclado)
        try:
            r = requests.post(f"{base}/{metodo}", json=dados, timeout=30)
            if r.ok:
                return True
            # imagem recusada pelo Telegram: tenta de novo so com texto
            if metodo == "sendPhoto":
                dados.pop("photo")
                dados["text"] = dados.pop("caption")
                r = requests.post(f"{base}/sendMessage", json=dados, timeout=30)
                if r.ok:
                    return True
            log.warning("telegram: %s", r.text[:300])
        except requests.RequestException as e:
            log.warning("telegram: %s", e)
        return False
