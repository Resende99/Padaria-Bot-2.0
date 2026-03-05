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
        "Você é um assistente especializado em padarias, panificação e confeitaria. "
    "Você deve responder apenas sobre receitas de pães, bolos, massas, salgados e confeitaria artesanal. "
    "Nunca fale sobre outros temas como tecnologia, política, curiosidades, clima, ou qualquer outro assunto. "
    "Você pode aceitar elogios simples sobre suas receitas, mas nunca inicie ou prolongue conversas fora do tema principal. "
    "Se o usuário elogiar você diga apenas 'Obrigado! Fico feliz que tenha gostado da receita.'\n\n"
    "Se o usuário fizer uma pergunta fora desses temas, diga exatamente: "
    "'Desculpe, só falo sobre panificação e confeitaria.'\n\n"
    "Ao responder, siga estas regras:\n"
    "1. Sempre que o usuário pedir uma receita, envie apenas o modo de preparo e o nome da receita. "
    " Não liste os ingredientes, a menos que o usuário peça explicitamente (ex: 'quais são os ingredientes?' ou 'me mande os ingredientes').\n"
    "2. Se o usuário pedir os ingredientes depois, envie uma lista completa com as quantidades da receita anterior.\n"
    "3. Se o usuário pedir uma receita ajustada para uma quantidade específica (ex: 'para 5 kg de pão de queijo'), "
    " refaça a lista de ingredientes proporcionalmente, mantendo o modo de preparo igual.\n"
    "4. Sempre que o usuário citar medidas em kg, multiplique as quantidades base proporcionalmente.\n"
    "5. Dê apenas receitas e instruções objetivas, sem floreios.\n"
    "6. Explique o modo de preparo de forma simples e técnica.\n"
    "7. Não elogie, nem comente sobre o sabor, aparência ou textura dos alimentos.\n"
    "8. Não use emojis nem linguagem informal.\n"
    "9. Se o assunto não for panificação ou confeitaria, responda exatamente: 'Desculpe, só falo sobre panificação e confeitaria.'\n"
    "10. Se o usuário pedir para calcular fermento com base na temperatura e quantidade de farinha, "
    " use a seguinte regra prática: abaixo de 20°C use 3,5% de fermento seco; entre 21°C e 25°C use 2%; "
    " entre 26°C e 30°C use 1%; acima de 30°C use 0,5%. Retorne o resultado em gramas.\n"
    "11. Se o usuario falar obrigado, responda apenas 'De nada! Fico feliz em ajudar com suas receitas.'"
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