# services/ia_services.py
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)


def gerar_resposta(pergunta: str, retries: int = 2, backoff: float = 2.0) -> str:
    api_key = os.getenv("API_KEY")
    if not api_key:
        logger.error("API_KEY não configurada")
        return "Erro: API_KEY não configurada."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": pergunta}],
        "temperature": 0.2,
    }

    attempt = 0
    while attempt <= retries:
        try:
            r = requests.post(url, headers=headers, json=data, timeout=25)
            if r.status_code != 200:
                logger.warning("Groq retornou status %s: %s", r.status_code, r.text[:200])
                raise RuntimeError(f"HTTP {r.status_code}")
            j = r.json()
            return j["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Tentativa %d falhou: %s", attempt + 1, exc)
            attempt += 1
            time.sleep(backoff ** attempt)

    return "Erro ao gerar resposta. Tente novamente mais tarde."