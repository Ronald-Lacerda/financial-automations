# CONTEXTO DO PROJETO F-HELPER

## Visão Geral

O `f-helper` é uma API de automação desenhada para simplificar o processo de solicitação de reembolso do fundo de obras junto à imobiliária Gonzaga. A API expõe um endpoint que, ao ser acionado, dispara um robô (bot) que baixa um comprovante, executa o processo de login no portal do cliente, e cria um ticket de solicitação com o comprovante anexado.

O sistema também notifica um **webhook** sobre o sucesso ou a falha da operação.

## Componentes Principais

### 1. `main.py`: A API FastAPI

Este arquivo é o ponto de entrada da aplicação. Ele utiliza o framework FastAPI para criar um servidor web com os seguintes endpoints:

- **`GET /`**:
    - **Função**: Health Check.
    - **Descrição**: Rota para verificar se o serviço está online.
    - **Resposta**: Retorna um JSON com o status `"health"`.

- **`POST /automate/reimbursement`**:
    - **Função**: Disparador da Automação.
    - **Descrição**: Rota principal que recebe os dados e agenda a função `run_condo_automation` para execução em segundo plano.
    - **Corpo da Requisição (JSON)**:
        - `url_file_comprovante` (string, URL): A URL pública do arquivo de comprovante a ser baixado e anexado.
        - `webhook_url` (string, URL): A URL que será notificada ao final do processo.
    - **Resposta**: Retorna uma mensagem confirmando que o fluxo foi iniciado.

### 2. `automation.py`: O Robô com Playwright e HTTX

Este módulo contém a lógica de automação. Ele usa `httpx` para operações de rede (download e webhook) e `playwright` para controle do navegador.

A função `run_condo_automation` executa os seguintes passos:

1.  **Download do Comprovante**: Baixa o arquivo a partir da `url_file_comprovante`. Se falhar, envia uma notificação de erro para o `webhook_url` e para a execução.
2.  **Carrega Credenciais**: Lê o usuário e a senha de um arquivo `.env`.
3.  **Inicia o Navegador**: Lança uma instância do Chromium em modo `headless`.
4.  **Fluxo de Login**: Acessa a área do cliente da Gonzaga, preenche as credenciais e entra no painel.
5.  **Navegação Pós-Login**: Navega até a página de criação de tickets.
6.  **Criação do Ticket**:
    - Preenche o formulário do ticket.
    - **Anexa o arquivo** que foi baixado no passo 1.
7.  **Gera Evidência**: Tira um "screenshot" da tela final.
8.  **Notificação de Webhook**: Envia uma mensagem de sucesso ou erro para o `webhook_url`.
9.  **Limpeza**: Remove os arquivos temporários criados durante o processo.
10. **Finaliza**: Fecha o navegador.

## Como Funciona

1.  Um sistema externo faz uma requisição `POST` para `/automate/reimbursement`, enviando as URLs no corpo da requisição.
2.  A API responde imediatamente e inicia a automação em background.
3.  O robô (`automation.py`) baixa o arquivo, faz login no portal, preenche o ticket e anexa o arquivo.
4.  Ao final, o webhook é notificado com o resultado, e um `screenshot_final.png` é salvo como evidência.

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (`fhelper/`) com as seguintes credenciais:
```
GONZAGA_USER="seu_usuario_aqui"
GONZAGA_PASS="sua_senha_aqui"
X_API_KEY="sua_chave_de_api_aqui"
```

## Dependências e Execução

### Instalação de Dependências

Este ambiente é gerenciado pelo sistema de pacotes `apt`. Para instalar as dependências necessárias, utilize os seguintes comandos:

```bash
# Atualiza a lista de pacotes
sudo apt-get update

# Instala as dependências de sistema
sudo apt-get install -y python3-fastapi python3-uvicorn python3-pydantic python3-dotenv python3-httpx
```

### Instalação do Playwright

O Playwright não está disponível via `apt` e precisa ser instalado com `pip`. Além disso, ele requer o download de binários de navegadores.

1.  **Instale o Playwright com pip:**
    ```bash
    pip install playwright
    ```

2.  **Instale os navegadores e dependências do sistema para o Playwright:**
    ```bash
    playwright install --with-deps
    ```

### Execução

Após instalar as dependências, existem duas maneiras de iniciar o serviço, dependendo do seu diretório atual:
** A partir de dentro do diretório `fhelper`**

Se você já estiver dentro da pasta `fhelper` use o seguinte comando:
```bash
python -m uvicorn main:app --reload
```
