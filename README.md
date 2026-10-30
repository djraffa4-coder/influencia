# InfluencIA

SaaS que gera roteiros de venda, fotos de influenciadores virtuais com o produto e videos com avatar, usando IA.

## Estrutura

```
app/
  main.py          # cria o app, CORS, paginas estaticas e registra as rotas
  config.py        # variaveis de ambiente, planos e limites mensais
  database.py      # conexao com o banco, get_db e migracao de colunas novas
  models.py        # tabelas (users, imagens, visita_demo, historico)
  seguranca.py     # senha, JWT, IP do visitante, limite de tentativas, chave de admin
  ia.py            # chamadas ao Gemini e gravacao das imagens no banco
  routes/
    contas.py      # cadastro, login, Google, redefinir senha, /me, /creditos
    geracao.py     # /gerar-script, /gerar-imagem, /gerar-video, /imagens/{id}
    pagamentos.py  # Mercado Pago (checkout + webhook) e evento Purchase no Meta
    admin.py       # /admin/* (exige a chave de admin)
    demo.py        # demo gratis da pagina inicial
static/            # frontend (index.html), exemplos e midia
```

## Rodar localmente

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha os valores
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```

Abra http://localhost:8000.

## Deploy (Render)

O `Procfile` ja inicia o app. Configure as variaveis do `.env.example` no painel do Render.
Na inicializacao o app cria as tabelas que faltam e adiciona colunas novas automaticamente.

## Admin

Envie a chave no cabecalho `X-Admin-Key` (recomendado):

```bash
curl -H "X-Admin-Key: $ADMIN_KEY" https://seu-app.onrender.com/admin/listar-usuarios
```

Ainda funciona `?admin_key=` por compatibilidade. Depois de 5 chaves erradas o IP fica bloqueado por 15 minutos.
