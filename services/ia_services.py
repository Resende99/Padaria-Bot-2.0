# services/ia_services.py
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _headers():
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY não configurada")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def gerar_resposta(pergunta: str, retries: int = 2, backoff: float = 2.0) -> str:
    """
    Gera resposta usando o Groq sem busca na web.
    Usado para receitas do PDF e fallback geral.
    """
    try:
        headers = _headers()
    except ValueError as e:
        return str(e)

    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": pergunta}],
        "temperature": 0.2,
    }

    attempt = 0
    while attempt <= retries:
        try:
            r = requests.post(GROQ_URL, headers=headers, json=data, timeout=25)
            if r.status_code != 200:
                logger.warning("Groq status %s: %s", r.status_code, r.text[:200])
                raise RuntimeError(f"HTTP {r.status_code}")
            return r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Tentativa %d falhou: %s", attempt + 1, exc)
            attempt += 1
            time.sleep(backoff ** attempt)

    return "Erro ao gerar resposta. Tente novamente mais tarde."


def buscar_e_responder_web(pergunta: str, retries: int = 2, backoff: float = 2.0) -> str:
    """
    Usa o modelo compound-beta do Groq que tem acesso à web nativo.
    Chamado quando a receita não é encontrada no PDF.
    """
    try:
        headers = _headers()
    except ValueError as e:
        return str(e)

    sistema = (
        "Você é um assistente especializado em panificação e confeitaria. "
        "Responda apenas sobre receitas de pães, bolos, massas, salgados e confeitaria. "
        "Busque a receita solicitada e responda de forma técnica e formatada:\n"
        "- Nome da receita\n"
        "- Modo de preparo (numerado)\n"
        "Não liste ingredientes a menos que o usuário peça. "
        "Não use emojis nem linguagem informal."
    )

    data = {
        "model": "compound-beta",
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": pergunta},
        ],
        "temperature": 0.2,
    }

    attempt = 0
    while attempt <= retries:
        try:
            r = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)
            if r.status_code != 200:
                logger.warning("Groq compound-beta status %s: %s", r.status_code, r.text[:200])
                raise RuntimeError(f"HTTP {r.status_code}")

            j = r.json()
            conteudo = j["choices"][0]["message"]["content"]
            return conteudo

        except Exception as exc:
            logger.warning("Tentativa %d falhou: %s", attempt + 1, exc)
            attempt += 1
            time.sleep(backoff ** attempt)

    # Fallback para modelo simples se compound-beta falhar
    return gerar_resposta(pergunta)