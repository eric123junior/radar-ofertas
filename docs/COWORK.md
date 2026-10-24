# Configuração pelo Claude Cowork

Copie o texto do bloco abaixo e cole numa conversa do Claude Cowork. Ele usa o
seu navegador, com os seus logins, para criar o app do Mercado Livre, cadastrar as
chaves no GitHub e disparar a primeira execução do radar.

Antes de começar, deixe o navegador logado no **Mercado Livre** e no **GitHub**.

```text
Quero configurar o meu projeto "radar-ofertas" (https://github.com/eric123junior/radar-ofertas).
Use o meu navegador, onde já estou logado no Mercado Livre e no GitHub.

REGRAS
- Nunca escreva a Client Secret no chat, em arquivos, notas ou em qualquer lugar além do
  campo de secret do GitHub. Copie e cole direto entre as páginas.
- Se aparecer aceite de termos, verificação por SMS/e-mail, pedido de documento, CPF,
  CNPJ ou qualquer pagamento: PARE e me peça para fazer essa parte.
- Não altere nada no repositório além do que está descrito aqui.
- Se algo na tela estiver diferente do descrito, escolha a opção mais simples e de
  menor permissão; se não tiver certeza, me pergunte.

ETAPA 1 - Criar o app de desenvolvedor do Mercado Livre (não é o programa de afiliados)
1. Abra https://developers.mercadolivre.com.br e entre em "Minhas aplicações"
   (ou "Criar aplicação").
2. Se eu já tiver uma aplicação chamada "Radar de Ofertas", use essa e pule para o passo 5.
3. Crie uma nova aplicação com:
   - Nome: Radar de Ofertas
   - Nome curto: radar-ofertas (se pedir)
   - Descrição: Monitor pessoal de ofertas do Mercado Livre
   - URI de redirect: https://github.com/eric123junior/radar-ofertas
   - Logo: pule, se for opcional
   - Permissões/escopos: apenas leitura. Não marque escrita, pagamentos, mensagens
     nem notificações (tópicos).
   - PKCE ou outras opções avançadas: deixe o padrão.
4. Salve.
5. Na página da aplicação, localize o "Client ID" (às vezes chamado "App ID") e a
   "Client Secret" (chave secreta).

ETAPA 2 - Cadastrar as chaves no GitHub
1. Abra https://github.com/eric123junior/radar-ofertas/settings/secrets/actions
2. Clique em "New repository secret" e crie:
   - Name: ML_CLIENT_ID     | Secret: o Client ID do passo anterior
3. Clique de novo em "New repository secret" e crie:
   - Name: ML_CLIENT_SECRET | Secret: a Client Secret do passo anterior
   (Se algum já existir, use "Update" para substituir o valor.)
4. Confira que os dois nomes aparecem na lista "Repository secrets", escritos exatamente assim.

ETAPA 3 - Palavras-chave (opcional)
1. Abra https://github.com/eric123junior/radar-ofertas/settings/variables/actions
2. Se ainda não existir, crie a variável:
   - Name: PALAVRAS
   - Value: fone bluetooth,smartwatch,air fryer,ssd,monitor,iphone,tv,notebook
   (Antes de salvar, me pergunte se quero mudar a lista.)

ETAPA 4 - Rodar o radar pela primeira vez
1. Abra https://github.com/eric123junior/radar-ofertas/actions/workflows/radar.yml
2. Se o GitHub pedir para habilitar os workflows, habilite.
3. Clique em "Run workflow", deixe a branch "main" e confirme.
4. Espere a execução terminar (de 1 a 3 minutos) e abra-a.
5. No job "rodar", abra o passo "Buscar e publicar ofertas" e copie as linhas do log
   que contêm: "lojas ativas", "mercadolivre", "passaram no filtro", "publicadas",
   e qualquer linha com "HTTP", "token" ou "nenhuma loja".
6. Abra https://github.com/eric123junior/radar-ofertas/blob/main/OFERTAS.md e veja se há ofertas.

RELATÓRIO FINAL (sem nenhuma chave ou secret)
- Se o app do Mercado Livre foi criado (só o nome dele)
- Se os secrets ML_CLIENT_ID e ML_CLIENT_SECRET aparecem no GitHub
- Se a variável PALAVRAS foi criada e com qual valor
- Resultado da execução (sucesso/falha) e as linhas do log copiadas
- Quantas ofertas apareceram no OFERTAS.md, e as 3 primeiras (produto, preço, desconto)
```

Depois, volte à conversa com o Claude Code e cole o relatório. Ele também
consegue ler o log da execução direto do GitHub para corrigir o que for preciso.
