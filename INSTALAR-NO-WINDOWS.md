# Central de Afiliados — instalador Windows

O instalador é produzido pelo GitHub Actions em um executor Windows. Ele empacota o Flask/Waitress e cria atalhos no Menu Iniciar e, opcionalmente, na Área de Trabalho.

## Dados do usuário
O banco e os uploads ficam em `%LOCALAPPDATA%\CentralDeAfiliados\instance`, fora da pasta do programa. A chave de sessão é criada uma vez em `%LOCALAPPDATA%\CentralDeAfiliados\secret.key`. Desinstalar o programa não deve apagar essa pasta de dados.

## Gerar
Abra a aba Actions do repositório e execute **Build instalador Windows**. Ao terminar com sucesso, baixe o artefato **CentralDeAfiliados-Instalador-Windows**.

## Observação
O instalador só deve ser distribuído depois que o workflow concluir e o aplicativo for validado em um Windows limpo. O primeiro acesso abre o navegador em http://127.0.0.1:5000.
