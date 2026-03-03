import os
import time
import logging
import requests

# importa o contexto e o conteúdo do PDF
from chat_padeiro import contexto_base, pdf_content

logger = logging.getLogger(__name__)


def gerar_resposta(pergunta: str, retries: int = 2, backoff: float = 2.0) -> str:

    api_key = os.getenv("API_KEY")

    if not api_key:
        logger.error("API_KEY não configurada")
        return "Erro: API_KEY não configurada."

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # monta contexto completo
    mensagem = f"""
{contexto_base}

Base de receitas extraída dos PDFs:
{pdf_content[:8000]}

Pergunta do usuário:
{pergunta}
"""

    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system",
                "content": "Você é um especialista em panificação e confeitaria."
            },
            {
                "role": "user",
                "content": mensagem
            }
        ]
    }

    attempt = 0

    while attempt <= retries:

        try:

            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=20
            )

            # verifica erro HTTP
            if response.status_code != 200:
                logger.error("Erro API Groq: %s", response.text)
                raise Exception("Erro na API")

            resposta = response.json()

            return resposta["choices"][0]["message"]["content"]

        except Exception as exc:

            logger.warning("Tentativa %d falhou: %s", attempt + 1, exc)

            attempt += 1

            time.sleep(backoff ** attempt)

    logger.error("Todas as tentativas falharam")

    return "Erro ao gerar resposta. Tente novamente mais tarde."