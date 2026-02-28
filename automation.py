import os
import asyncio
import httpx
import uuid
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Carrega as variáveis do arquivo .env
load_dotenv()

# --- Funções Auxiliares ---

async def send_webhook_notification(webhook_url: str, message: str, success: bool = False):
    """Envia uma notificação para a URL de webhook especificada."""
    try:
        async with httpx.AsyncClient() as client:
            payload = {"status": "success" if success else "error", "message": message}
            print(f"LOG: 📢 Enviando notificação para webhook: {payload}")
            await client.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"LOG: ⚠️ Falha ao enviar notificação para o webhook: {e}")

async def run_condo_automation(url_file_comprovante: str, webhook_url: str):
    """
    Executa a automação completa: baixa o comprovante, faz login, e cria o ticket.
    """
    user = os.getenv("GONZAGA_USER")
    pw = os.getenv("GONZAGA_PASS")
    waha_api_key = os.getenv("WAHA_API_KEY")
    
    # Cria um diretório os comprovantes baixados
    comprov_dir = Path(f"./comprovantes")
    comprov_dir.mkdir(exist_ok=True)
    local_file_path = ""

    # Cria diretório para Screenshots
    screenshot_dir = Path(f"./screenshots")
    screenshot_dir.mkdir(exist_ok=True)

    # --- Bloco de Download ---
    try:
        headers = {
            "X-Api-Key": waha_api_key
        }
        print(f"LOG: 📥 Baixando arquivo de {url_file_comprovante} com chave de API...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url_file_comprovante, 
                headers=headers, 
                follow_redirects=True, 
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"Falha ao baixar o arquivo. Status: {response.status_code}. Resposta: {response.text}"
                print(f"LOG: ❌ {error_msg}")
                #await send_webhook_notification(webhook_url, error_msg)
                return

            file_extension = Path(url_file_comprovante).suffix or '.jpeg'
            local_file_path = comprov_dir / f"comprovante_{uuid.uuid4()}{file_extension}"
            with open(local_file_path, "wb") as f:
                f.write(response.content)
            print(f"LOG: ✅ Arquivo salvo em: {local_file_path}")

    except Exception as e:
        error_msg = f"Ocorreu um erro inesperado durante o download: {e}"
        print(f"LOG: ❌ {error_msg}")
        #await send_webhook_notification(webhook_url, error_msg)
        return

    # --- Bloco de Automação com Playwright ---
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=500, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        
        try:
            print("LOG: 🌐 Acessando login...")
            await page.goto("https://areacliente.gonzagaimoveis.com.br", wait_until="networkidle")

            print("LOG: ✍️ Preenchendo usuário...")
            await page.fill('input[name="username"]', user)
            await page.click('button.index__get-user-btn', force=True)
            
            selector_ronald = 'button:has-text("Ronald Batista Gambini Lacerda")'
            await page.wait_for_selector(selector_ronald, timeout=10000)
            await page.click(selector_ronald)

            print("LOG: ✍️ Preenchendo senha...")
            await page.fill('input[name="password"]', pw)
            await page.click('button:has-text("Acessar")', force=True)

            print("LOG: ⏳ Aguardando carregamento do painel interno...")
            await page.wait_for_selector('text=Tickets', timeout=15000)

            await page.locator('div.client__link-content', has_text="Tickets").click()
            await page.get_by_text("Criar Novo Ticket").wait_for(state="visible")
            await page.get_by_text("Criar Novo Ticket").click()

            print("LOG: 📋 Preenchendo os detalhes do ticket...")
            await page.select_option('select#setor', value="117")
            await page.select_option('select#assunto', value="103")
            await page.fill('textarea[name="ticket-anotacao"]', "Olá, gostaria de solicitar os descontos do boleto do condomínio em anexo.")

            print(f"LOG: 📎 Anexando o arquivo {local_file_path}...")
            await page.set_input_files('input#file', local_file_path)
            await page.wait_for_timeout(2000) 

            screenshot_name = f"ticket_preenchido-{uuid.uuid4()}.png"
            await page.screenshot(path=screenshot_dir / screenshot_name)
            print("LOG: ✅ Ticket preenchido e anexo enviado!")
            
            # await send_webhook_notification(webhook_url, "Automação de ticket concluída com sucesso.", success=True)

        except Exception as e:
            error_msg = f"Erro durante a automação com Playwright: {e}"
            print(f"LOG: ❌ {error_msg}")
            await page.screenshot(path="erro_debug.png")
            #await send_webhook_notification(webhook_url, error_msg)
        finally:
            await browser.close()