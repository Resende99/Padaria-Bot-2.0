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


# ====== CONTEXTO BASE ======
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


# ====== MELHORIA 1: LEITURA DO PDF COM TEXTO LIMPO ======
def limpar_espacos_pdf(texto: str) -> str:
    """Remove espaços duplos entre palavras causados por PDFs mal formatados."""
    # Remove espaços múltiplos entre palavras
    texto = re.sub(r" {2,}", " ", texto)
    # Remove espaço antes de pontuação
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

                    # Linha muito curta = provavelmente palavra quebrada
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


def limpar_cache_periodico():
    global cache
    while True:
        time.sleep(3600)
        cache = carregar_cache()


threading.Thread(target=limpar_cache_periodico, daemon=True).start()


def buscar_no_pdf(mensagem: str):
    """
    Busca no PDF e retorna o bloco completo da receita encontrada.
    Detecta o início da receita pelo número + nome (ex: '1. Sorvete')
    e captura até o início da próxima receita.
    """
    if not pdf_content:
        return None

    texto_lower = pdf_content.lower()
    termos = re.findall(r"[a-zà-ú]{4,}", mensagem.lower())
    stop = {"receita", "como", "fazer", "para", "quero", "preciso", "pode", "dias", "quentes", "frios", "manda", "qual"}
    termos = [t for t in termos if t not in stop]

    padrao_cabecalho = re.compile(r"(?m)^\d+\.\s+[A-Za-záéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ][^\n]{2,}")

    for t in termos[:8]:
        pos = texto_lower.find(t)
        if pos == -1:
            continue

        # Recua até o início do bloco da receita
        trecho_antes = pdf_content[max(0, pos - 800):pos]
        m = None
        for match in padrao_cabecalho.finditer(trecho_antes):
            m = match
        if m:
            inicio = max(0, pos - 800) + m.start()
        else:
            inicio = max(0, pos - 200)

        # Avança até o próximo cabeçalho de receita
        trecho_depois = pdf_content[pos:min(len(pdf_content), pos + 2000)]
        proximo = padrao_cabecalho.search(trecho_depois[10:])
        if proximo:
            fim = pos + 10 + proximo.start()
        else:
            fim = min(len(pdf_content), pos + 2000)

        return pdf_content[inicio:fim].strip()

    return None




def normalizar_texto_pdf(txt: str) -> str:
    txt = (txt or "").replace("\r", "")
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


# ====== MELHORIA 2: EXTRAÇÃO E FORMATAÇÃO COMO HUMANO ======
def extrair_receita_do_trecho(trecho: str):
    """
    Extrai nome, ingredientes e modo de preparo.
    Suporta o padrão do PDF: bullet ●, numeração inline, múltiplas seções.
    """
    t = normalizar_texto_pdf(trecho)
    # Remove cabeçalho [PDF: ...]
    t = re.sub(r"\[PDF:[^\]]+\]", "", t).strip()

    linhas = [l.strip() for l in t.splitlines() if l.strip()]

    nome = None
    ingredientes_blocos = []   # lista de (titulo_secao, [linhas])
    modo_blocos = []           # lista de (titulo_secao, [linhas])
    secao_atual = None
    titulo_secao = ""
    buffer_linhas = []

    def fechar_secao():
        nonlocal buffer_linhas
        if secao_atual == "ingredientes" and buffer_linhas:
            ingredientes_blocos.append((titulo_secao, list(buffer_linhas)))
        elif secao_atual == "modo" and buffer_linhas:
            modo_blocos.append((titulo_secao, list(buffer_linhas)))
        buffer_linhas = []

    for linha in linhas:
        linha_lower = linha.lower()
        linha_limpa = re.sub(r"^[●•\-]\s*", "", linha).strip()

        # Detecta nome (primeira linha tipo "1. Sorvete" ou só o nome)
        if nome is None:
            m_nome = re.match(r"^\d+\.\s+(.+)$", linha_limpa)
            if m_nome:
                nome = m_nome.group(1).strip()
                continue
            elif not any(p in linha_lower for p in ["ingrediente", "modo", "preparo", "kg", " g ", "ml", "xícara", "colher", "litro", "●"]):
                if 3 < len(linha_limpa) < 80:
                    nome = linha_limpa
                    continue

        # Detecta seção Ingredientes (com variações: "Ingredientes (Mousse):", etc)
        if re.search(r"ingredientes?", linha_lower):
            fechar_secao()
            secao_atual = "ingredientes"
            titulo_secao = re.sub(r".*ingredientes?\s*", "", linha_limpa, flags=re.I).strip(":() ")
            # Ingredientes inline (tudo na mesma linha após o :)
            inline = re.sub(r".*ingredientes?[^:]*:\s*", "", linha, flags=re.I).strip()
            if inline and len(inline) > 5:
                for parte in inline.split(","):
                    parte = parte.strip()
                    if parte:
                        buffer_linhas.append(parte)
            continue

        # Detecta seção Modo de Preparo
        if re.search(r"modo\s*de\s*preparo", linha_lower):
            fechar_secao()
            secao_atual = "modo"
            titulo_secao = re.sub(r".*modo\s*de\s*preparo\s*", "", linha_limpa, flags=re.I).strip(":() ")
            continue

        # Ignora linhas de observação (Obs, Nota, Dica, Finalização)
        if re.match(r"^(obs|nota|dica|finaliz)", linha_lower):
            continue

        # Acumula por seção
        if secao_atual == "ingredientes":
            # Remove numeração do item (1. 2. etc)
            item = re.sub(r"^\d+\.\s*", "", linha_limpa).strip()
            if item:
                buffer_linhas.append(item)
        elif secao_atual == "modo":
            item = re.sub(r"^\d+\.\s*", "", linha_limpa).strip()
            if item:
                buffer_linhas.append(item)

    fechar_secao()

    # Monta ingredientes formatados
    partes_ing = []
    for titulo, linhas_ing in ingredientes_blocos:
        if titulo:
            partes_ing.append(f"({titulo})")
        for i, l in enumerate(linhas_ing, 1):
            partes_ing.append(f"{i}. {l}")
    ingredientes = "\n".join(partes_ing) if partes_ing else None

    # Monta modo formatado
    partes_modo = []
    for titulo, linhas_modo in modo_blocos:
        if titulo:
            partes_modo.append(f"({titulo})")
        for i, l in enumerate(linhas_modo, 1):
            partes_modo.append(f"{i}. {l}")
    modo = "\n".join(partes_modo) if partes_modo else None

    return nome, ingredientes, modo


def formatar_receita(nome: str, ingredientes: str, modo: str, pedir_ingredientes: bool):
    if not nome or not modo:
        return None

    if pedir_ingredientes and ingredientes:
        return f"Receita: {nome}\n\nIngredientes:\n{ingredientes}\n\nModo de preparo:\n{modo}"

    return f"Receita: {nome}\n\nModo de preparo:\n{modo}"


# ====== MELHORIA 3: CÁLCULO PROPORCIONAL COM BASE REAL DO PDF ======
def detectar_base_kg(trecho: str) -> float:
    """Detecta para quantos kg a receita original foi feita."""
    m = re.search(r"(?i)receita\s+para\s+(\d+(?:[.,]\d+)?)\s*kg", trecho)
    if m:
        return float(m.group(1).replace(",", "."))
    return 1.0  # assume 1kg se não encontrar


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
    # DEVE vir antes de qualquer busca no PDF
    if "fermento" in mensagem.lower():
        # Pega o primeiro número como farinha (kg) e o segundo como temperatura
        numeros = re.findall(r"(\d+(?:[.,]\d+)?)", mensagem)
        farinha_match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem, re.I)
        temp_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|graus?|celsius|grau)", mensagem, re.I)

        # Fallback: se não achou com palavras, usa os dois primeiros números
        farinha_val = farinha_match.group(1) if farinha_match else (numeros[0] if len(numeros) >= 1 else None)
        temp_val = temp_match.group(1) if temp_match else (numeros[1] if len(numeros) >= 2 else None)

        if farinha_val and temp_val:
            fermento = calcular_fermento(farinha_val, temp_val)
            if fermento is not None:
                return jsonify({"resposta": f"Para {farinha_val} kg de farinha a {temp_val}\u00b0C, use {fermento} g de fermento seco."}), 200
            return jsonify({"resposta": "Valores inválidos. Verifique os números informados."}), 200

        # Faltam dados — orienta o usuário
        return jsonify({"resposta": "Para calcular o fermento, preciso de duas informações:\n\n1. Quantidade de farinha (em kg)\n2. Temperatura ambiente (em °C)\n\nDigite assim: \"calcular fermento para 2 kg com temperatura 28 graus\""}), 200

    # flags do pedido
    pediu_ingredientes = bool(re.search(r"\bingrediente\b", mensagem.lower()))
    kg_desejado = detectar_kg_pedido(mensagem)

    # Ingredientes da última receita (pedido separado)
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

    # 1) tenta PDF primeiro e FORMATA
    trecho = buscar_no_pdf(mensagem)
    if trecho:
        nome, ingredientes, modo = extrair_receita_do_trecho(trecho)

        # salva última receita completa para pedidos posteriores
        if nome:
            session["ultima_receita_nome"] = nome
        if ingredientes:
            session["ultima_receita_ingredientes"] = ingredientes
        if modo:
            session["ultima_receita_modo"] = modo

        # MELHORIA 3: detecta base real do PDF antes de calcular fator
        if kg_desejado and ingredientes:
            base = detectar_base_kg(trecho)
            session["ultima_receita_base_kg"] = base
            fator = kg_desejado / base
            ingredientes = multiplicar_ingredientes(ingredientes, fator)
            pediu_ingredientes = True

        resposta_pdf = formatar_receita(nome or "Receita do PDF", ingredientes or "", modo or trecho, pediu_ingredientes)
        if not resposta_pdf:
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