from fastapi import FastAPI, BackgroundTasks, HTTPException, status
import re
from dotenv import load_dotenv
import os
from automation import run_condo_automation

# Carrega as variáveis do arquivo .env
load_dotenv()

app = FastAPI(
    title="F-Helper API",
    description="API para automação de reembolso de fundo de obra",
    version="1.0.0"
)

def clean_url(value: str) -> str:
    """Extrai a URL pura caso ela venha formatada como Markdown [link](url)"""
    if not value or not isinstance(value, str):
        return value
    # Procura por algo dentro de (http...)
    match = re.search(r'\((https?://[^\)]+)\)', value)
    if match:
        return match.group(1)
    return value.strip("[]") # Remove colchetes se sobrarem

@app.get("/", tags=["System"])
async def health_check():
    """Verifica se a API está online e operante."""
    return {"status": "health", "service": "f-helper"}

@app.post("/automate/reimbursement", status_code=status.HTTP_202_ACCEPTED, tags=["Automation"])
async def trigger_reimbursement(payload: dict, background_tasks: BackgroundTasks):
    """
    Recebe um payload JSON, extrai as URLs e dispara a automação em segundo plano.
    Retorna 202 (Accepted) para indicar que a tarefa foi aceita.
    """
    try:
        # Navegação segura no JSON para encontrar as URLs
        raw_file_url = payload.get("body", {}).get("payload", {}).get("media", {}).get("url")
        callback_webhook_url = os.getenv("CALLBACK_WEBHOOK_URL")

        file_url = clean_url(raw_file_url)

        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível encontrar 'url' do arquivo no payload JSON."
            )

        # Adiciona a automação para ser executada em background
        background_tasks.add_task(run_condo_automation, file_url, callback_webhook_url)

        return {
            "status": "accepted",
            "detail": "O fluxo de automação foi aceito e está sendo processado em segundo plano.",
            "file_url": file_url,
            "webhook_callback_url": callback_webhook_url
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Se ocorrer qualquer outro erro durante o processamento do payload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao processar o payload da requisição: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)