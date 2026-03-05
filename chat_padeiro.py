# chat_padeiro.py
from flask import Flask, render_template, request, jsonify, session
import os
import json
import time
import threading
import re
import random

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from services.ia_services import gerar_resposta, buscar_e_responder_web

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_trocar")

CACHE_FILE = "receitas_cache.json"
PDF_FOLDER = "pdfs_upload"
os.makedirs(PDF_FOLDER, exist_ok=True)

pdf_content = ""


# ══════════════════════════════════════════
# CACHE
# ══════════════════════════════════════════
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

def limpar_cache_periodico():
    global cache
    while True:
        time.sleep(3600)
        cache = carregar_cache()

threading.Thread(target=limpar_cache_periodico, daemon=True).start()


# ══════════════════════════════════════════
# CONTEXTO BASE DA IA
# ══════════════════════════════════════════
contexto_base = (
    "Você é um assistente especializado em padarias, panificação e confeitaria. "
    "Responda apenas sobre receitas de pães, bolos, massas, salgados e confeitaria artesanal. "
    "Se o usuário elogiar, diga apenas: 'Obrigado! Fico feliz que tenha gostado da receita.' "
    "Se a pergunta for fora do tema, diga: 'Desculpe, só falo sobre panificação e confeitaria.'\n\n"
    "Regras de resposta:\n"
    "1. Ao pedir receita: envie apenas o nome e o modo de preparo. Não liste ingredientes a menos que peçam.\n"
    "2. Se pedirem ingredientes depois: envie lista completa com quantidades.\n"
    "3. Se pedirem receita para X kg: recalcule os ingredientes proporcionalmente.\n"
    "4. Respostas objetivas e técnicas. Sem floreios, emojis ou linguagem informal.\n"
    "5. Não comente sabor, aparência ou textura.\n"
    "6. Para cálculo de fermento: abaixo de 20 use 3,5%; 21-25 use 2%; 26-30 use 1%; acima de 30 use 0,5%. Resultado em gramas.\n"
)


# ══════════════════════════════════════════
# CÁLCULO DE FERMENTO
# ══════════════════════════════════════════
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


# ══════════════════════════════════════════
# PDF — LEITURA
# ══════════════════════════════════════════
def limpar_espacos_pdf(texto):
    texto = re.sub(r" {2,}", " ", texto)
    texto = re.sub(r" ([.,;:!?])", r"\1", texto)
    return texto

def extrair_texto_pdf(caminho_pdf):
    if not PDF_SUPPORT:
        return ""
    try:
        texto = ""
        with open(caminho_pdf, "rb") as f:
            leitor = PdfReader(f)
            for pagina in leitor.pages:
                texto_pagina = pagina.extract_text() or ""
                texto_pagina = limpar_espacos_pdf(texto_pagina)
                linhas = texto_pagina.splitlines()
                linhas_limpas = []
                buffer = ""
                for linha in linhas:
                    linha = linha.strip()
                    if not linha:
                        if buffer:
                            linhas_limpas.append(buffer)
                            buffer = ""
                        linhas_limpas.append("")
                        continue
                    if len(linha) < 25 and not linha.endswith((".", ":", ",")):
                        buffer = (buffer + " " + linha).strip()
                    else:
                        if buffer:
                            linhas_limpas.append((buffer + " " + linha).strip())
                            buffer = ""
                        else:
                            linhas_limpas.append(linha)
                if buffer:
                    linhas_limpas.append(buffer)
                texto += "\n".join(linhas_limpas) + "\n\n"
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


# ══════════════════════════════════════════
# PDF — BUSCA
# ══════════════════════════════════════════
CATALOGO_RECEITAS = {
    "Sorvete":                           ["sorvete"],
    "Mousse de Cafe com Chocolate":      ["mousse", "cafe"],
    "Bolo de Abacaxi com Doce de Leite": ["abacaxi", "doce de leite"],
    "Bolo de Fuba":                      ["fuba"],
    "Bolo Cacarola":                     ["cacarola"],
    "Bolo de Chocolate":                 ["peteleco", "chocolate"],
    "Bolo Pudim":                        ["pudim"],
}

# Nomes reais no PDF (com acentos)
NOMES_PDF = {
    "Sorvete":                           "Sorvete",
    "Mousse de Cafe com Chocolate":      "Mousse de Café com Chocolate",
    "Bolo de Abacaxi com Doce de Leite": "Bolo de Abacaxi com Doce de Leite",
    "Bolo de Fuba":                      "Bolo de Fubá",
    "Bolo Cacarola":                     "Bolo Caçarola",
    "Bolo de Chocolate":                 "Bolo de Chocolate",
    "Bolo Pudim":                        "Bolo Pudim",
}


def normalizar_str(s):
    import unicodedata
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


def buscar_no_pdf(mensagem):
    if not pdf_content:
        return None

    msg_norm = normalizar_str(mensagem)

    chave_encontrada = None
    for chave, keywords in CATALOGO_RECEITAS.items():
        if any(k in msg_norm for k in keywords):
            chave_encontrada = chave
            break

    if not chave_encontrada:
        return None

    nome_real = NOMES_PDF[chave_encontrada]
    idx = pdf_content.find(nome_real)
    if idx == -1:
        return None

    # Captura até o proximo nome de receita
    fim = len(pdf_content)
    for outro_nome in NOMES_PDF.values():
        if outro_nome == nome_real:
            continue
        pos = pdf_content.find(outro_nome, idx + len(nome_real))
        if pos != -1 and pos < fim:
            fim = pos

    return pdf_content[idx:fim].strip()

def normalizar_texto_pdf(txt):
    txt = (txt or "").replace("\r", "")
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def extrair_receita_do_trecho(trecho):
    linhas = [l.strip() for l in trecho.splitlines() if l.strip()]

    nome = None
    ingredientes_linhas = []
    modo_linhas = []
    secao = None

    for linha in linhas:
        linha_lower = linha.lower()
        linha_limpa = linha.strip()

        # Nome: primeira linha que nao seja secao
        if nome is None:
            if not any(p in linha_lower for p in ["ingrediente", "modo de preparo", "receitas para"]):
                nome = linha_limpa
                continue

        # Detecta secao Ingredientes
        if linha_lower.strip() == "ingredientes":
            secao = "ingredientes"
            continue

        # Detecta secao Modo de Preparo
        if "modo de preparo" in linha_lower:
            secao = "modo"
            continue

        # Separadores de subsecao ([ Massa ], [ Cobertura ], etc)
        if re.match(r"^\[.+\]$", linha_limpa):
            if secao == "ingredientes":
                label = linha_limpa.strip("[] ")
                ingredientes_linhas.append("--- " + label + " ---")
            continue

        # Ignora obs/dica
        if re.match(r"^(obs|dica|nota)", linha_lower):
            continue

        if secao == "ingredientes":
            item = re.sub(r"^\d+\.\s*", "", linha_limpa).strip()
            if item:
                ingredientes_linhas.append(item)
        elif secao == "modo":
            item = re.sub(r"^\d+\.\s*", "", linha_limpa).strip()
            if item:
                modo_linhas.append(item)

    ingredientes = None
    if ingredientes_linhas:
        partes = []
        for l in ingredientes_linhas:
            if l.startswith("---"):
                partes.append("\n" + l)
            else:
                partes.append("  " + l)
        ingredientes = "\n".join(partes).strip()

    modo = None
    if modo_linhas:
        modo = "\n".join(str(i) + ". " + l for i, l in enumerate(modo_linhas, 1))

    return nome, ingredientes, modo

def formatar_receita(nome, ingredientes, modo, pedir_ingredientes):
    if not nome or not modo:
        return None
    # Remove qualquer referência ao arquivo PDF do nome
    nome = re.sub(r"\[PDF:[^\]]+\]", "", nome).strip()
    nome = re.sub(r"Receitas\s+para\s+Dias\s+\w+", "", nome, flags=re.I).strip()
    nome = nome.strip("[]()., ")
    if not nome:
        return None
    if pedir_ingredientes and ingredientes:
        return f"Receita: {nome}\n\nIngredientes:\n{ingredientes}\n\nModo de preparo:\n{modo}"
    return f"Receita: {nome}\n\nModo de preparo:\n{modo}"


# ══════════════════════════════════════════
# BUSCA NA WEB
# ══════════════════════════════════════════
def buscar_receita_web(mensagem):
    """Usa o Groq compound-beta que tem acesso nativo à web."""
    try:
        return buscar_e_responder_web(mensagem)
    except Exception as e:
        print(f"Erro busca web: {e}")
        return None


# ══════════════════════════════════════════
# ESCALA POR KG
# ══════════════════════════════════════════
def detectar_base_kg(trecho):
    m = re.search(r"(?i)receita\s+para\s+(\d+(?:[.,]\d+)?)\s*kg", trecho)
    return float(m.group(1).replace(",", ".")) if m else 1.0

def detectar_kg_pedido(mensagem):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem.lower())
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except:
        return None

def multiplicar_ingredientes(ingredientes_texto, fator):
    linhas = [l.strip() for l in (ingredientes_texto or "").splitlines() if l.strip()]
    out = []
    for linha in linhas:
        m = re.match(r"^(\d+(?:[.,]\d+)?)\s*(.*)$", linha)
        if m:
            num = float(m.group(1).replace(",", "."))
            novo = num * fator
            novo_str = str(int(round(novo))) if abs(novo - round(novo)) < 1e-9 else str(round(novo, 2)).replace(".", ",")
            out.append(f"{novo_str} {m.group(2)}".strip())
        else:
            out.append(linha)
    return "\n".join(out)


# ══════════════════════════════════════════
# ROTAS
# ══════════════════════════════════════════
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

    historico = session.get("historico", [])
    historico.append(mensagem)
    session["historico"] = historico[-3:]
    ultima_receita = session.get("ultima_receita", "")

    # ══ 1. FERMENTO — intercepta antes de tudo ══
    aguardando_fermento = session.get("aguardando_fermento", False)

    # Detecta pedido de CÁLCULO de fermento:
    # - usuário já estava no fluxo (aguardando_fermento=True), OU
    # - mensagem tem "fermento" + "calcul/temperatura/grau/kg" ou números
    msg_lower = mensagem.lower()
    palavras_calculo = ["calcul", "temperatura", "grau", "celsius", "quanto", "preciso"]
    tem_numero = bool(re.search(r"\d", mensagem))
    eh_calculo_fermento = aguardando_fermento or (
        "fermento" in msg_lower and (
            any(p in msg_lower for p in palavras_calculo) or tem_numero
        )
    )

    if eh_calculo_fermento:
        numeros = re.findall(r"(\d+(?:[.,]\d+)?)", mensagem)
        farinha_match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem, re.I)
        temp_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|graus?|celsius|grau)", mensagem, re.I)

        farinha_val = farinha_match.group(1) if farinha_match else (numeros[0] if len(numeros) >= 1 else None)
        temp_val = temp_match.group(1) if temp_match else (numeros[1] if len(numeros) >= 2 else None)

        if farinha_val and temp_val:
            session["aguardando_fermento"] = False
            # Delega cálculo ao Groq para garantir precisão
            prompt_fermento = (
                f"Calcule a quantidade de fermento seco para panificação.\n"
                f"Farinha: {farinha_val} kg | Temperatura ambiente: {temp_val}°C\n\n"
                f"Use estas regras:\n"
                f"- Abaixo de 20°C: 3,5% do peso da farinha\n"
                f"- Entre 21°C e 25°C: 2%\n"
                f"- Entre 26°C e 30°C: 1%\n"
                f"- Acima de 30°C: 0,5%\n\n"
                f"Responda apenas com o resultado no formato:\n"
                f"Para X kg de farinha a Y°C, use Z g de fermento seco."
            )
            resposta_fermento = gerar_resposta(prompt_fermento)
            return jsonify({"resposta": resposta_fermento}), 200
        
        return jsonify({"resposta": "Valores inválidos. Verifique os números informados."}), 200

        session["aguardando_fermento"] = True
        return jsonify({"resposta": "Para calcular o fermento, preciso de duas informações:\n\n1. Quantidade de farinha (em kg)\n2. Temperatura ambiente (em °C)\n\nDigite assim: \"2 kg, 28 graus\""}), 200

    # ══ 2. DIAS QUENTES / FRIOS — lista de receitas disponíveis ══
    RECEITAS_QUENTES = ["Sorvete", "Mousse de Café com Chocolate", "Bolo de Abacaxi com Doce de Leite"]
    RECEITAS_FRIAS = ["Bolo de Fubá", "Bolo Caçarola", "Bolo de Chocolate", "Bolo Pudim"]

    if re.search(r"dias?.quentes?", msg_lower):
        # Pega receitas já enviadas para não repetir
        enviadas = session.get("quentes_enviadas", [])
        disponiveis = [r for r in RECEITAS_QUENTES if r not in enviadas]
        if not disponiveis:
            # Resetou tudo, começa de novo
            enviadas = []
            disponiveis = RECEITAS_QUENTES[:]
        escolhida = random.choice(disponiveis)
        enviadas.append(escolhida)
        session["quentes_enviadas"] = enviadas
        session["ultima_categoria"] = "quentes"
        # Busca a receita no PDF ou IA
        mensagem = f"receita de {escolhida}"
        msg_lower = mensagem.lower()

    if re.search(r"dias?.frios?", msg_lower):
        enviadas = session.get("frias_enviadas", [])
        disponiveis = [r for r in RECEITAS_FRIAS if r not in enviadas]
        if not disponiveis:
            enviadas = []
            disponiveis = RECEITAS_FRIAS[:]
        escolhida = random.choice(disponiveis)
        enviadas.append(escolhida)
        session["frias_enviadas"] = enviadas
        session["ultima_categoria"] = "frias"
        mensagem = f"receita de {escolhida}"
        msg_lower = mensagem.lower()

    # Usuário pediu mais receitas da mesma categoria
    if re.search(r"(mais|outra|proxima|próxima)", msg_lower) and session.get("ultima_categoria"):
        cat = session.get("ultima_categoria")
        if cat == "quentes":
            mensagem = "Receitas para dias quentes"
        else:
            mensagem = "Receitas para dias frios"
        msg_lower = mensagem.lower()
        # Redireciona para o bloco acima — chama recursivamente via redirect interno
        enviadas = session.get(f"{cat}_enviadas", [])
        lista = RECEITAS_QUENTES if cat == "quentes" else RECEITAS_FRIAS
        disponiveis = [r for r in lista if r not in enviadas]
        if not disponiveis:
            enviadas = []
            disponiveis = lista[:]
        escolhida = random.choice(disponiveis)
        enviadas.append(escolhida)
        session[f"{cat}_enviadas"] = enviadas
        mensagem = f"receita de {escolhida}"
        msg_lower = mensagem.lower()

    # ══ 3. FILTRO DE TEMA ══
    # Palavras que indicam assunto fora de panificação
    temas_proibidos = [
        "politic", "futebol", "tecnologia", "programação", "clima", "tempo",
        "notícia", "filme", "música", "jogo", "esporte", "economia",
        "presidente", "governo", "medicina", "saúde", "covid", "vacina",
        "computador", "celular", "carro", "viagem", "hotel"
    ]
    # Palavras que indicam panificação (libera a busca)
    temas_permitidos = [
        "receita", "bolo", "pão", "massa", "recheio", "cobertura", "sorvete",
        "mousse", "confeit", "padaria", "forno", "assar", "ingrediente",
        "farinha", "fermento", "açúcar", "manteiga", "leite", "ovo",
        "chocolate", "creme", "brigadeiro", "salgado", "torta", "biscoito",
        "cookie", "croissant", "brioche", "fubá", "tapioca"
    ]
    
    eh_tema_proibido = any(t in msg_lower for t in temas_proibidos)
    eh_tema_permitido = any(t in msg_lower for t in temas_permitidos)
    
    if eh_tema_proibido and not eh_tema_permitido:
        return jsonify({"resposta": "Desculpe, só falo sobre panificação e confeitaria."}), 200

    # ══ 4. FLAGS ══
    pediu_ingredientes = bool(re.search(r"\bingrediente\b", mensagem.lower()))
    kg_desejado = detectar_kg_pedido(mensagem)

    if pediu_ingredientes and not kg_desejado:
        last_nome = session.get("ultima_receita_nome") or ultima_receita
        last_ing = session.get("ultima_receita_ingredientes", "")
        if last_ing:
            return jsonify({"resposta": f"Receita: {last_nome}\n\nIngredientes:\n{last_ing}"}), 200
        if ultima_receita:
            mensagem = f"Liste apenas os ingredientes da receita: {ultima_receita}"
        else:
            return jsonify({"resposta": "Não sei de qual receita você está falando."}), 200

    chave_cache = f"{mensagem}|{ultima_receita}"
    if chave_cache in cache:
        return jsonify({"resposta": cache[chave_cache]}), 200

    # ══ 5. BUSCA NO PDF ══
    trecho = buscar_no_pdf(mensagem)
    if trecho:
        nome, ingredientes, modo = extrair_receita_do_trecho(trecho)

        if nome:
            session["ultima_receita_nome"] = nome
        if ingredientes:
            session["ultima_receita_ingredientes"] = ingredientes
        if modo:
            session["ultima_receita_modo"] = modo

        if kg_desejado and ingredientes:
            base = detectar_base_kg(trecho)
            ingredientes = multiplicar_ingredientes(ingredientes, kg_desejado / base)
            pediu_ingredientes = True

        resposta_pdf = formatar_receita(nome or "Receita", ingredientes or "", modo or trecho, pediu_ingredientes)
        if not resposta_pdf:
            resposta_pdf = f"Encontrei isso na base de receitas:\n\n{trecho}"

        cache[chave_cache] = resposta_pdf
        salvar_cache()
        return jsonify({"resposta": resposta_pdf}), 200

    # ══ 6. BUSCA NA WEB ══
    resposta_web = buscar_receita_web(mensagem)
    if resposta_web:
        cache[chave_cache] = resposta_web
        salvar_cache()
        match = re.search(r"(?i)(receita de|para fazer)\s+([a-zà-ú\s]+)", mensagem)
        if match:
            session["ultima_receita"] = match.group(2).strip().lower()
        return jsonify({"resposta": resposta_web}), 200

    # ══ 7. FALLBACK IA ══
    contexto = contexto_base + "\n\nHistórico:\n" + "\n".join(historico)
    if pdf_content:
        contexto += f"\n\n[CONTEÚDO DOS PDFs]\n{pdf_content[:6000]}"

    prompt = f"{contexto}\nUsuário: {mensagem}"
    resposta = gerar_resposta(prompt)

    cache[chave_cache] = resposta
    salvar_cache()

    match = re.search(r"(?i)(receita de|para fazer)\s+([a-zà-ú\s]+)", mensagem)
    if match:
        session["ultima_receita"] = match.group(2).strip().lower()

    return jsonify({"resposta": resposta}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)