from flask import Flask, render_template, request, jsonify, session
import os
import json
import time
import threading

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("PyPDF2 não instalado. Suporte a PDF desabilitado.")

app = Flask(__name__)

# chave de sessão
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

CACHE_FILE = "receitas_cache.json"
PDF_FOLDER = "pdfs_upload"

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

pdf_content = ""

# =========================
# CACHE
# =========================

def carregar_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

cache = carregar_cache()

# =========================
# CONTEXTO DO BOT
# =========================

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
    "Não liste os ingredientes, a menos que o usuário peça explicitamente.\n"
    "2. Se o usuário pedir os ingredientes depois, envie a lista completa.\n"
    "3. Ajuste ingredientes proporcionalmente quando pedirem quantidades.\n"
    "4. Multiplique ingredientes corretamente quando citarem kg.\n"
    "5. Dê apenas receitas e instruções objetivas.\n"
    "6. Explique o modo de preparo de forma simples.\n"
    "7. Não elogie o sabor.\n"
    "8. Não use emojis.\n"
    "9. Fora do tema responda: 'Desculpe, só falo sobre panificação e confeitaria.'\n"
    )

# ========================= 
# CÁLCULO DE FERMENTO
# =========================

def calcular_fermento(kg, temp):
    try:
        kg = float(kg.replace(",", "."))
        temp = float(temp.replace(",", "."))

        if kg <= 0 or temp < 0:
            return None

        p = 0.035 if temp < 20 else 0.02 if temp <= 25 else 0.01 if temp <= 30 else 0.005
        return round(kg * 1000 * p, 1)

    except:
        return None

# =========================
# EXTRAIR TEXTO PDF
# =========================

def extrair_texto_pdf(caminho_pdf):

    try:

        texto = ""

        with open(caminho_pdf, "rb") as f:

            leitor = PdfReader(f)

            for pagina in leitor.pages:

                texto += pagina.extract_text() + "\n"

        return texto.strip()

    except Exception as e:

        print("Erro ao extrair PDF:", e)

        return ""

# =========================
# CARREGAR PDFs
# =========================

def carregar_pdfs_pasta():

    global pdf_content

    if not os.path.exists(PDF_FOLDER):
        return

    for arquivo in os.listdir(PDF_FOLDER):

        if arquivo.endswith(".pdf"):

            caminho = os.path.join(PDF_FOLDER, arquivo)

            texto = extrair_texto_pdf(caminho)

            pdf_content += f"\n\n[PDF: {arquivo}]\n{texto}"

            print("PDF carregado:", arquivo)


carregar_pdfs_pasta()

# =========================
# LIMPAR CACHE
# =========================

def limpar_cache_periodico():

    while True:

        time.sleep(3600)

        global cache

        cache = carregar_cache()


threading.Thread(target=limpar_cache_periodico, daemon=True).start()

# =========================
# ROTAS
# =========================

@app.route("/")
def index():
    return render_template("index.html")

# upload de pdf

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():

    global pdf_content

    try:

        if "pdf" not in request.files:
            return jsonify({"erro": "Nenhum arquivo enviado"}), 400

        file = request.files["pdf"]

        if not file.filename.endswith(".pdf"):
            return jsonify({"erro": "Apenas PDF permitido"}), 400

        caminho = os.path.join(PDF_FOLDER, file.filename)

        file.save(caminho)

        if PDF_SUPPORT:

            texto = extrair_texto_pdf(caminho)

            pdf_content += "\n\n[PDF: " + file.filename + "]\n" + texto

            return jsonify({"status": "ok", "mensagem": "PDF carregado com sucesso"})

        else:

            return jsonify({"erro": "PyPDF2 não instalado"}), 500

    except Exception as e:

        return jsonify({"erro": str(e)}), 500

# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)