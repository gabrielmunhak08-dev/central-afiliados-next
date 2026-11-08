# Central de Afiliados — plano oficial

## Objetivo

Manter uma aplicação privada para organizar produtos de afiliado Shopee, preparar conteúdo para Instagram, planejar publicações e acompanhar resultados. A interface prioriza celular; um notebook Windows funciona como servidor contínuo, acessado externamente por HTTPS.

## Regras do projeto

- Não inventar preços, descontos, comissões, tendências ou resultados.
- Diferenciar dados retornados pela API, dados importados de páginas e informações preenchidas manualmente.
- Não publicar automaticamente no Instagram sem integração oficial validada e autorização explícita.
- Não guardar senhas em texto puro nem incluir chaves de API no Git.
- Fazer backup antes de atualizações de banco, código ou arquivos de mídia.
- Testar cada etapa antes de declarar que está pronta.
- Priorizar soluções gratuitas e informar custos de serviços externos antes de ativá-los.
- O GitHub é a fonte do código. O notebook executa somente o servidor.

## Estado implementado

1. **Painel:** totais de produtos e publicações cadastradas.
2. **Catálogo:** cadastro e edição, categorias, preço, link de afiliado, comissão informada, observações e até 10 fotos por produto.
3. **Fotos privadas:** arquivos armazenados fora do diretório estático e servidos apenas após autenticação.
4. **Pesquisa Shopee:** tela preservada; busca automática temporariamente pausada durante a reconstrução da integração.
5. **Importação por link:** leitura conservadora de metadados e JSON-LD da página quando disponíveis. A consulta complementar à API foi retirada; valores precisam ser revisados e comissão não é inferida de texto genérico.
6. **Marketing:** cadastro e organização de Stories e Feed, legendas, imagens, status e configurações de conteúdo.
7. **Geração com IA:** tela, seleção de produtos e configurações preservadas; geração automática temporariamente pausada durante a reconstrução da integração.
8. **Calendário:** agenda semanal básica, com tarefas, horário, categoria de tarefa e status.
9. **Acesso:** primeiro usuário administrador, autenticação, proteção CSRF e administração de usuários.

## Pendências e próximas etapas

1. Reconstruir a integração Shopee em módulo isolado, com credenciais protegidas e testes próprios.
2. Reconstruir a integração de geração de imagens por IA em módulo isolado, preservando fotos, regras e fluxo de aprovação.
3. Validar cada integração com credenciais autorizadas antes de ativá-la.
4. Revisar a experiência do calendário editorial e sua utilização em celular.
5. Criar módulos de métricas e análise apenas quando houver dados reais de cliques, pedidos, vendas e comissões.
6. Revisar continuamente autenticação, privacidade de imagens, backups e recuperação.

## Arquitetura e implantação

- Python + Flask para a aplicação web.
- SQLite para o banco local, em `instance/central.sqlite3` por padrão.
- Arquivos de mídia privados em `instance/uploads/` por padrão.
- Waitress como servidor WSGI, limitado a `127.0.0.1`; acesso externo exclusivamente por túnel HTTPS.
- Configurações sensíveis em `.env` local ou variáveis do ambiente, nunca versionadas.
- GitHub Actions para testes automatizados.

## Limites de validação

As integrações antigas da Shopee e do Gemini foram retiradas nesta etapa. As telas relacionadas permanecem disponíveis, mas não executam chamadas externas até a reconstrução e validação de cada integração.

Não existe publicação automática no Instagram nesta versão. A revisão final, o adesivo de link, a música e a publicação ficam sob controle do usuário.