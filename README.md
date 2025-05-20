# Teleinformática e Redes 2

## Introdução

Siga estes passos para configurar e executar o projeto em um sistema Linux:

### Pré-requisitos

- Python 3.x instalado

### Como executar

1. Execute `python3 -m venv tr2_p2p`
2. Execute `source tr2_p2p/bin/activate`
3. Execute `python3 ./tracker/server.py`
4. Em outro terminal, execute `python3 ./peer/client.py`
5. Teste a interface!

## Estrutura de Pastas

O projeto segue a seguinte estrutura de pastas:

- O diretório `peer/` contém o código cliente do projeto, incluindo a interface de terminal.
- O diretório `tracker/` contém os códigos do tracker do projeto, incluindo o código do servidor, banco de dados e peers.

Essa estrutura organizada ajuda a manter o projeto limpo e facilita a manutenção e expansão do código.
