# chat_padeiro.py
from flask import Flask, render_template, request, jsonify, session
import os
import json
import time
import threading
import re

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from services.ia_services import gerar_resposta

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_trocar")

CACHE_FILE = "receitas_cache.json"
PDF_FOLDER = "pdfs_upload"
os.makedirs(PDF_FOLDER, exist_ok=True)

pdf_content = ""


def carregar_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


cache = carregar_cache()


def salvar_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass


# ====== MANTIDO: CONTEXTO BASE ======
contexto_base = (
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
)


def calcular_fermento(kg, temp):
    try:
        kg = float(str(kg).replace(",", "."))
        temp = float(str(temp).replace(",", "."))
        if kg <= 0 or temp < 0:
            return None
        p = 0.035 if temp < 20 else 0.02 if temp <= 25 else 0.01 if temp <= 30 else 0.005
        return round(kg * 1000 * p, 1)
    except:
        return None


def extrair_texto_pdf(caminho_pdf):
    if not PDF_SUPPORT:
        return ""
    try:
        texto = ""
        with open(caminho_pdf, "rb") as f:
            leitor = PdfReader(f)
            for pagina in leitor.pages:
                texto += (pagina.extract_text() or "") + "\n"
        return texto.strip()
    except:
        return ""


def carregar_pdfs_pasta():
    global pdf_content
    pdf_content = ""
    if not os.path.exists(PDF_FOLDER):
        return
    for arquivo in os.listdir(PDF_FOLDER):
        if arquivo.lower().endswith(".pdf"):
            caminho = os.path.join(PDF_FOLDER, arquivo)
            texto = extrair_texto_pdf(caminho)
            if texto:
                pdf_content += f"\n\n[PDF: {arquivo}]\n{texto}"
                print(f"PDF carregado: {arquivo}")


carregar_pdfs_pasta()


def limpar_cache_periodico():
    global cache
    while True:
        time.sleep(3600)
        cache = carregar_cache()


threading.Thread(target=limpar_cache_periodico, daemon=True).start()


def buscar_no_pdf(mensagem: str):
    """Busca simples: retorna um trecho do PDF se achar palavra-chave relevante."""
    if not pdf_content:
        return None

    texto_lower = pdf_content.lower()
    termos = re.findall(r"[a-zà-ú]{4,}", mensagem.lower())
    stop = {"receita", "como", "fazer", "para", "quero", "preciso", "pode", "dias", "quentes", "frios"}
    termos = [t for t in termos if t not in stop]

    for t in termos[:8]:
        pos = texto_lower.find(t)
        if pos != -1:
            inicio = max(0, pos - 600)
            fim = min(len(pdf_content), pos + 1200)
            return pdf_content[inicio:fim].strip()

    return None


# ====== NOVO: FORMATAR RECEITA DO PDF (NOME + MODO, INGREDIENTES SÓ SE PEDIR) ======
def normalizar_texto_pdf(txt: str) -> str:
    txt = (txt or "").replace("\r", "")
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def extrair_receita_do_trecho(trecho: str):
    """
    Retorna (nome, ingredientes, modo).
    Funciona melhor quando o trecho contém 'Ingredientes' e 'Modo de Preparo'.
    """
    t = normalizar_texto_pdf(trecho)

    nome = None
    ingredientes = None
    modo = None

    # Nome (linha antes de Ingredientes)
    m_nome = re.search(r"(?im)^\s*(.+?)\s*\n\s*●?\s*Ingredientes\s*:?", t)
    if m_nome:
        nome = m_nome.group(1).strip()
    else:
        # fallback: primeira linha não vazia
        linhas = [l.strip() for l in t.splitlines() if l.strip()]
        if linhas:
            nome = linhas[0][:80]

    m_ing = re.search(r"(?is)Ingredientes\s*:?(.*?)(Modo\s*de\s*Preparo\s*:?)", t)
    if m_ing:
        ingredientes = m_ing.group(1).strip()

    m_modo = re.search(r"(?is)Modo\s*de\s*Preparo\s*:?(.*)$", t)
    if m_modo:
        modo = m_modo.group(1).strip()

    return nome, ingredientes, modo


def formatar_receita(nome: str, ingredientes: str, modo: str, pedir_ingredientes: bool) -> str | None:
    if not nome or not modo:
        return None

    if pedir_ingredientes and ingredientes:
        return f"Receita: {nome}\n\nIngredientes:\n{ingredientes}\n\nModo de preparo:\n{modo}"

    return f"Receita: {nome}\n\nModo de preparo:\n{modo}"


# ====== NOVO: AJUSTE PROPORCIONAL POR KG (ingredientes) ======
def detectar_kg_pedido(mensagem: str):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem.lower())
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except:
        return None


def multiplicar_ingredientes(ingredientes_texto: str, fator: float) -> str:
    linhas = [l.strip() for l in (ingredientes_texto or "").splitlines() if l.strip()]
    out = []

    for linha in linhas:
        m = re.match(r"^(\d+(?:[.,]\d+)?)\s*(.*)$", linha)
        if m:
            num = float(m.group(1).replace(",", "."))
            resto = m.group(2)
            novo = num * fator

            if abs(novo - round(novo)) < 1e-9:
                novo_str = str(int(round(novo)))
            else:
                novo_str = str(round(novo, 2)).replace(".", ",")

            out.append(f"{novo_str} {resto}".strip())
        else:
            out.append(linha)

    return "\n".join(out)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/v1/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    global pdf_content
    if "pdf" not in request.files:
        return jsonify({"erro": "Nenhum arquivo fornecido"}), 400

    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"erro": "Apenas PDFs são aceitos"}), 400

    caminho = os.path.join(PDF_FOLDER, file.filename)
    file.save(caminho)

    carregar_pdfs_pasta()
    return jsonify({"status": "ok", "mensagem": f"PDF '{file.filename}' carregado com sucesso!"}), 200


@app.route("/api/v1/chat", methods=["POST"])
def api_chat():
    dados = request.get_json() or {}
    mensagem = (dados.get("mensagem") or "").strip()

    if not mensagem:
        return jsonify({"resposta": "Digite algo."}), 200

    # sessão básica
    historico = session.get("historico", [])
    historico.append(mensagem)
    historico = historico[-3:]
    session["historico"] = historico

    ultima_receita = session.get("ultima_receita", "")

    # Regra: cálculo de fermento
    if "fermento" in mensagem.lower() and "temperatura" in mensagem.lower():
        farinha = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem, re.I)
        temp = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|graus|c)", mensagem, re.I)
        if farinha and temp:
            fermento = calcular_fermento(farinha.group(1), temp.group(1))
            if fermento is not None:
                return jsonify({"resposta": f"Para {farinha.group(1)} kg de farinha a {temp.group(1)}°C, use {fermento} g de fermento seco."}), 200
            return jsonify({"resposta": "Valores inválidos."}), 200
        return jsonify({"resposta": "Informe farinha (kg) e temperatura (°C)."}), 200

    # flags do pedido
    pediu_ingredientes = bool(re.search(r"\bingrediente\b", mensagem.lower()))
    kg_desejado = detectar_kg_pedido(mensagem)

    # Ingredientes da última receita (pedido separado)
    if pediu_ingredientes and not kg_desejado:
        # Se já salvamos uma receita completa na sessão, entrega ingredientes dela
        last_nome = session.get("ultima_receita_nome") or ultima_receita
        last_ing = session.get("ultima_receita_ingredientes", "")
        if last_ing:
            return jsonify({"resposta": f"Receita: {last_nome}\n\nIngredientes:\n{last_ing}"}), 200
        if ultima_receita:
            # fallback: pede para IA listar ingredientes
            mensagem = f"Liste apenas os ingredientes da receita: {ultima_receita}"
        else:
            return jsonify({"resposta": "Não sei de qual receita você está falando."}), 200

    chave_cache = f"{mensagem}|{ultima_receita}"
    if chave_cache in cache:
        return jsonify({"resposta": cache[chave_cache]}), 200

    # 1) tenta PDF primeiro e FORMATA
    trecho = buscar_no_pdf(mensagem)
    if trecho:
        nome, ingredientes, modo = extrair_receita_do_trecho(trecho)

        # salva última receita completa para pedidos posteriores (ingredientes / escala)
        if nome:
            session["ultima_receita_nome"] = nome
        if ingredientes:
            session["ultima_receita_ingredientes"] = ingredientes
        if modo:
            session["ultima_receita_modo"] = modo

        # Se o usuário pediu X kg, ajusta ingredientes proporcionalmente (base assumida 1 kg)
        if kg_desejado and ingredientes:
            base = float(session.get("ultima_receita_base_kg", 1.0))
            fator = kg_desejado / base
            ingredientes = multiplicar_ingredientes(ingredientes, fator)
            pediu_ingredientes = True  # ao ajustar kg, sempre manda ingredientes ajustados

        resposta_pdf = formatar_receita(nome or "Receita do PDF", ingredientes or "", modo or trecho, pediu_ingredientes)
        if not resposta_pdf:
            # fallback se não conseguiu separar bem
            resposta_pdf = f"Encontrei isso na base de receitas:\n\n{trecho}"

        cache[chave_cache] = resposta_pdf
        salvar_cache()
        return jsonify({"resposta": resposta_pdf}), 200

    # 2) fallback IA (com PDF + regras)
    contexto = contexto_base + "\n\nHistórico:\n" + "\n".join(historico)
    if pdf_content:
        contexto += f"\n\n[CONTEÚDO DE PDFs CARREGADOS]\n{pdf_content[:6000]}"

    prompt = f"{contexto}\nUsuário: {mensagem}"
    resposta = gerar_resposta(prompt)

    cache[chave_cache] = resposta
    salvar_cache()

    # tenta capturar ultima_receita
    match = re.search(r"(?i)(receita de|para fazer)\s+([a-zà-ú\s]+)", mensagem)
    if match:
        session["ultima_receita"] = match.group(2).strip().lower()

    return jsonify({"resposta": resposta}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)