# Integração com a Shopee Affiliate Open API

## Estado atual

O projeto contém um cliente GraphQL assinado em `shopee_affiliate.py` e uma tela privada em `/produtos/buscar-shopee`. A busca usa a operação `productOfferV2`, mostra até 10 resultados por consulta e não grava produtos no catálogo automaticamente.

Os testes simulam as respostas da API. Ainda é necessário validar a conexão com credenciais reais e permissões autorizadas da conta.

## Credenciais

Configure no arquivo `.env` local do notebook ou nas variáveis de ambiente:

- `SHOPEE_APP_ID`: AppID disponibilizado na Open API.
- `SHOPEE_APP_SECRET`: segredo da aplicação gerado pela Shopee; não é a senha da conta.

Os segredos não devem ser enviados pelo chat, incluídos em templates, no banco, no Git ou em capturas de tela. O arquivo `.env` está no `.gitignore`.

## Endpoint e assinatura

Endpoint utilizado:

`https://open-api.affiliate.shopee.com.br/graphql`

O corpo JSON é serializado uma única vez e a mesma string é usada na assinatura SHA-256:

`SHA256(AppID + timestamp Unix em segundos + corpo JSON exato + secret)`

O cabeçalho segue o formato:

`Authorization: SHA256 Credential=..., Timestamp=..., Signature=...`

A camada de transporte substitui erros HTTP e GraphQL por mensagens resumidas, sem incluir cabeçalhos ou segredos.

## Busca e cadastro

- A pesquisa exige palavra-chave e envia `keyword`, `sortType`, `page` e `limit`.
- A tela exibe nome, loja, preço, vendas, avaliação, desconto e comissão quando a API os retorna.
- Resultados não são salvos automaticamente; confira preço e comissão no painel de afiliados antes de cadastrar ou publicar.
- A importação por link do catálogo é um fluxo separado. Ela tenta ler dados estruturados presentes na página da Shopee; não extrai comissão de texto genérico e pode não funcionar em páginas que exigem JavaScript ou bloqueiam acesso automatizado.
- Ainda falta a ação para selecionar um resultado da API e registrá-lo diretamente no catálogo com confirmação.

## Testes

Execute `python -m pytest -q`. Os testes do cliente simulam HTTP e GraphQL; não precisam de credenciais reais e não substituem o teste de conexão com a conta.