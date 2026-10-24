# Radar de Ofertas

Caça ofertas relâmpago nas lojas oficiais (Amazon, Mercado Livre, Shopee e lojas
das redes Lomadee e Awin, como Magalu e Americanas) e **passagens aéreas abaixo do
preço normal** (Travelpayouts/Aviasales), gera o seu link de afiliado e publica as
melhores num canal do Telegram e numa vitrine web.

Tudo roda sozinho no GitHub Actions de hora em hora: sem servidor e sem custo.

```
lojas (APIs oficiais) ──► nota 0-100 ──► filtro ──► Telegram
                              ▲                └──► vitrine (site/)
                    histórico de preços (SQLite)
```

## Passagens aéreas (Travelpayouts)

Em passagem não existe "preço de/por": a promoção é **o preço bem abaixo do normal
daquela rota**. Por isso o radar:

1. busca, a partir de `ORIGEM` (padrão `SAO`, que cobre Guarulhos, Congonhas e Viracopos),
   o menor preço para cada destino e as **tarifas especiais** que a própria Aviasales
   marca como abaixo do normal;
2. guarda o preço de cada rota (ida e volta e só ida separados) a cada execução;
3. com 5 ou mais registros, usa a **mediana** como "preço normal" e aprova a passagem
   que estiver `DESCONTO_MINIMO_VIAGEM`% abaixo (padrão 25%);
4. a tarifa especial entra mesmo antes de haver histórico;
5. a mesma rota não é repetida em 24 h, mesmo em outra data, a não ser que caia mais 3%.

Nos primeiros dias saem quase só as tarifas especiais. Conforme o histórico cresce,
o radar passa a reconhecer as quedas de preço de cada rota.

### Configuração

1. Crie a conta grátis em [travelpayouts.com](https://www.travelpayouts.com/) e entre
   no programa **Aviasales** (aprovação imediata, sem exigência de vendas).
2. Em **Perfil > Token da API**, copie o **token** e o **marker** (seu id de afiliado).
3. No GitHub, crie os secrets `TP_TOKEN` e `TP_MARKER`.
4. (Opcional) variáveis `ORIGEM`, `DESCONTO_MINIMO_VIAGEM`, `NOTA_MINIMA_VIAGEM`.
5. Rode **Actions > Diagnostico** para conferir o acesso e depois **Radar de ofertas**.

## Começando sem afiliação (só o Mercado Livre)

> **Atenção:** em outubro de 2026 o Mercado Livre passou a bloquear (HTTP 403,
> "PolicyAgent") busca, catálogo, mais vendidos e tendências para apps novos, com
> token de app ou de usuário. O roteiro abaixo continua aqui para quando o acesso
> for liberado; o workflow **Diagnostico** mostra na hora se já foi.

Dá para ligar o radar antes de entrar em qualquer programa de afiliados. As
ofertas saem com o link direto da loja e sem o aviso de afiliado. Quando você
se afiliar, basta cadastrar os parâmetros e os links passam a gerar comissão.

1. Entre em [developers.mercadolivre.com.br](https://developers.mercadolivre.com.br)
   com a sua conta do Mercado Livre e clique em **Criar aplicação**.
   - Nome e descrição: qualquer um (ex.: "Radar de Ofertas").
   - URI de redirect: `https://github.com/eric123junior/radar-ofertas`
   - Permissões: só leitura já basta.
2. Copie o **Client ID** (também chamado de App ID) e a **Client Secret**.
3. No GitHub: **Settings > Secrets and variables > Actions > New repository secret**:
   - `ML_CLIENT_ID` com o Client ID
   - `ML_CLIENT_SECRET` com a Client Secret
4. **Actions > Radar de ofertas > Run workflow**. Em ~1 minuto as ofertas aparecem
   no arquivo [`OFERTAS.md`](OFERTAS.md) do repositório.

Prefere que o Claude Cowork faça esses passos no seu navegador? Use o roteiro em
[`docs/COWORK.md`](docs/COWORK.md).

Para ver a vitrine pelo navegador, ative o GitHub Pages (veja "Vitrine" abaixo).

## Por que API oficial e não raspagem

Os programas de afiliados oferecem APIs próprias. Elas entregam preço, desconto e
o link de afiliado já rastreado, e não quebram quando o site muda de layout.
Raspar as páginas das lojas viola os termos dos programas, e isso pode levar ao
bloqueio da sua conta de afiliado e à perda das comissões.

## O que conta como "oportunidade"

Cada oferta recebe uma nota de 0 a 100 (`radar/pontuacao.py`):

| Sinal | Pontos |
|---|---|
| Desconto (40% = 20 pts, 80% ou mais = 40 pts) | até 40 |
| Menor preço já registrado no histórico | até 20 |
| Urgência: selo de relâmpago ou do dia, termina em poucas horas | até 20 |
| Escassez: pouco estoque restante | até 10 |
| Confiança: avaliação e volume de vendas | até 10 |
| Desconto falso: preço mais de 10% acima do menor já visto | −15 |

Só sai no canal o que passa por `DESCONTO_MINIMO` (40% por padrão) **e** por
`NOTA_MINIMA` (60 por padrão), ordenado pela nota. Uma oferta já enviada só volta
a sair depois de `HORAS_SEM_REPETIR`, ou antes disso se o preço cair mais 3%.
Ofertas que acabam em menos de 5 minutos são descartadas.

Com o tempo o histórico cresce e o filtro fica mais esperto, porque passa a
reconhecer o "de R$ 500 por R$ 250" de um produto que sempre custou R$ 250.

## Configuração

### 1. Credenciais de cada programa (configure só os que já tiver)

| Loja | Onde conseguir | Variáveis |
|---|---|---|
| **Amazon** | associados.amazon.com.br > Ferramentas > Product Advertising API. A API só libera depois de 3 vendas qualificadas em 180 dias e deixa de responder se a conta ficar 30 dias sem vendas. | `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, `AMAZON_TAG` |
| **Mercado Livre** | App grátis em developers.mercadolivre.com.br (veja acima). Os parâmetros de afiliado vêm do painel de Afiliados do ML e são opcionais. | `ML_CLIENT_ID`, `ML_CLIENT_SECRET`; afiliado: `ML_MATT_TOOL`, `ML_MATT_WORD` (ou `ML_LINK_AFILIADO`) |
| **Shopee** | affiliate.shopee.com.br > Open API | `SHOPEE_APP_ID`, `SHOPEE_SECRET` |
| **Lomadee** | developer.lomadee.com (app token e source id) | `LOMADEE_APP_TOKEN`, `LOMADEE_SOURCE_ID` |
| **Awin** | Toolbox > Create-a-Feed, um feed CSV por anunciante aprovado | `AWIN_FEEDS` (URLs separadas por vírgula) |

### 2. Bot do Telegram

1. Fale com o [@BotFather](https://t.me/BotFather), use `/newbot` e guarde o token.
2. Crie o canal e adicione o bot como **administrador**.
3. `TELEGRAM_TOKEN=<token>` e `TELEGRAM_CHAT_ID=@seucanal`.

### 3. No GitHub

- **Settings > Secrets and variables > Actions > Secrets**: todas as chaves acima.
- **Settings > Secrets and variables > Actions > Variables** (opcionais):
  `PALAVRAS`, `DESCONTO_MINIMO`, `NOTA_MINIMA`, `PRECO_MAXIMO`, `MAX_POR_EXECUCAO`,
  `PUBLICAR_PAGES`.
- **Actions**: habilite os workflows. O "Radar de ofertas" roda de hora em hora
  e também pelo botão *Run workflow*. Em repositório privado o plano grátis tem
  2.000 minutos/mês e cada execução conta pelo menos 1 minuto: de hora em hora dá
  ~720. Em repositório público os minutos são ilimitados e dá para usar `*/15`.

O workflow guarda o histórico (`estado/radar.db`), a vitrine (`site/ofertas.json`)
e a lista legível (`OFERTAS.md`) no próprio repositório depois de cada execução.

### 4. Vitrine

`site/index.html` é estática e lê `site/ofertas.json`. Para publicar no GitHub Pages:

1. **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. Crie a variável `PUBLICAR_PAGES` com o valor `true`.

A cada execução a vitrine é republicada em `https://eric123junior.github.io/radar-ofertas/`.
Em repositório **privado** o Pages só existe nos planos pagos do GitHub (Pro ou
superior). Sem plano pago, há duas saídas: tornar o repositório público (as chaves
continuam protegidas nos Secrets) ou conectar a pasta `site/` a um serviço
gratuito como Netlify ou Cloudflare Pages. Enquanto isso, use o `OFERTAS.md`.

## Rodando localmente

```bash
pip install -r requirements.txt
cp .env.example .env          # preencha as chaves
python -m radar --teste       # mostra o que seria enviado, sem enviar nada
python -m radar --teste --palavras "iphone,ps5"
python -m radar               # envia de verdade
python -m unittest discover -s tests -v
```

## Estrutura

```
radar/
  __main__.py       fluxo: coletar > pontuar > filtrar > publicar
  config.py         variáveis de ambiente / .env
  modelo.py         Oferta (formato único para todas as lojas)
  pontuacao.py      nota 0-100
  banco.py          histórico de preços e anti-repetição (SQLite)
  fontes/           amazon, mercadolivre, shopee, redes (lomadee + awin), travelpayouts
ferramentas/        diagnósticos das APIs (rodam pelo workflow Diagnostico)
  canais/           telegram, vitrine
site/index.html     vitrine
tests/              testes sem rede (respostas de exemplo de cada API)
```

## Boas práticas e regras

- Toda mensagem e a vitrine avisam que o link é de afiliado, como pedem o CONAR
  e os termos dos programas.
- Os links da vitrine usam `rel="sponsored"`.
- Respeite os limites de cada API. Com muitas palavras-chave, aumente o
  intervalo do cron.
- Os formatos de resposta da Lomadee e dos feeds Awin variam por conta e por
  anunciante. Se algum campo vier vazio, ajuste o conversor em `radar/fontes/redes.py`.

## Próximos passos sugeridos

- Cruzeiros, hotéis e pacotes (fontes em avaliação).
- Envio para grupos de WhatsApp (API oficial do WhatsApp Business).
- Encurtador próprio com contagem de cliques por oferta.
- Busca por categoria e "ofertas do dia" de cada loja, além das palavras-chave.
