# Central de Afiliados

Aplicação privada para organizar produtos de afiliado Shopee, preparar conteúdo para Instagram e planejar a rotina de publicações. A interface é responsiva e prioriza o uso pelo celular; o notebook Windows atua somente como servidor.

## Funcionalidades presentes

- **Acesso e usuários:** configuração do primeiro administrador, login, hash de senha, proteção CSRF e administração de usuários.
- **Catálogo:** cadastro e edição de produtos, categorias, preço, comissão informada, link de afiliado e galeria de até 10 fotos.
- **Importação por link:** ao colar um link de afiliado, a Central tenta resolver o produto, consulta nome, preço e taxa de comissão na API oficial quando identifica os IDs e as credenciais estão configuradas. A descrição é lida dos metadados/JSON-LD da página quando disponíveis, pois não faz parte dos campos de ProductOfferV2. Revise os dados antes de salvar.
- **Busca oficial Shopee:** consulta ofertas por `productOfferV2` e mostra os resultados para avaliação. A busca não cadastra produtos automaticamente nesta versão.
- **Marketing:** organização de conteúdo de Story e Feed, legenda, imagens e status de aprovação/publicação.
- **Criação com IA:** usa as fotos cadastradas e as regras salvas para gerar uma arte com Gemini. A imagem entra como aguardando aprovação; não existe publicação automática no Instagram.
- **Calendário:** agenda semanal básica para compromissos e tarefas. A experiência visual e a gestão editorial ainda podem evoluir.

## O que ainda não está concluído

- Importar diretamente um resultado da pesquisa Shopee para o catálogo com confirmação do usuário.
- Paginação completa da pesquisa Shopee e validação ao vivo com as credenciais reais da conta.
- Painel de métricas de cliques, pedidos, vendas e comissão conectado a dados reais.
- Revisão e evolução do calendário editorial.
- Publicação automática no Instagram. O compartilhamento e a publicação continuam sob controle do usuário.

Não considere uma integração validada até que o teste seja feito com uma conta e credenciais autorizadas. Os testes automatizados simulam a resposta dos serviços externos e não confirmam acesso real.

## Requisitos

- Python 3.12 recomendado.
- Windows 10/11 ou Linux.
- `CENTRAL_SECRET_KEY` forte e exclusiva da instalação.
- Credenciais Shopee e chave Gemini somente quando os respectivos recursos forem usados.

## Instalação no notebook servidor

1. Instale as dependências de execução:

```powershell
python -m pip install -r requirements.txt
```

2. Copie `.env.example` para `.env` na pasta do projeto e preencha os valores localmente. O arquivo `.env` é ignorado pelo Git e nunca deve ser enviado ao repositório.

3. Para acesso pela internet através de um túnel HTTPS, mantenha `CENTRAL_COOKIE_SECURE=1`. Para teste exclusivamente local via `http://127.0.0.1`, use `CENTRAL_COOKIE_SECURE=0`.

4. Inicie o servidor:

```powershell
python app.py
```

O Waitress atende somente em `127.0.0.1:5000` por padrão. O acesso externo deve passar por um túnel HTTPS confiável apontando para `http://127.0.0.1:5000`; não exponha a porta do Waitress diretamente à internet nem use o servidor de desenvolvimento do Flask.

Na primeira abertura, acesse `/configurar` e crie a conta inicial. Essa primeira conta recebe o perfil de administrador. Use uma senha forte com pelo menos 12 caracteres.

## Dados e privacidade

- Banco padrão: `instance/central.sqlite3`.
- Fotos e artes privadas: `instance/uploads/`.
- Os arquivos enviados são verificados como imagens reais, com limites de tamanho e dimensão.
- A rota `/uploads/...` exige login. A rota pública `/static/uploads/...` é bloqueada.
- O aplicativo pode migrar fotos antigas de `static/uploads/` para a pasta privada na inicialização. A cópia é conferida antes de remover o arquivo antigo; em caso de conflito, a inicialização para sem apagar o original.
- Faça backup da pasta `instance/` e do `.env` antes de atualizar o servidor. Não inclua o `.env` em backups compartilhados.

## Testes

Instale as dependências de desenvolvimento e execute:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

O GitHub Actions executa a mesma suíte em push para `main` e em pull requests direcionados à `main`.

## Fluxo de atualização do projeto

O código é atualizado no GitHub e revisado com testes antes da publicação. O notebook não é usado para desenvolver ou editar arquivos: ele somente executa o servidor e recebe a versão aprovada.

Não versionar segredos, bancos de dados, fotos, uploads nem arquivos locais de ambiente.