// static/script.js
document.addEventListener("DOMContentLoaded", () => {
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");

  if (!chatBox || !userInput || !sendBtn) return;

  function appendMessage(content, className) {
    const msg = document.createElement("div");
    msg.classList.add("message", className);
    msg.textContent = content;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
  }

  function setLoading(isLoading) {
    sendBtn.disabled = isLoading;
    userInput.disabled = isLoading;
  }

  async function enviarParaAPI(mensagem) {
    const resp = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem })
    });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      const detalhe = data?.error || data?.erro || "";
      throw new Error(detalhe || `HTTP ${resp.status}`);
    }

    return data?.resposta ?? "";
  }

  async function sendMessage(textFromButton = null) {
    const text = (textFromButton ?? userInput.value).trim();
    if (!text) return;

    appendMessage(text, "user-message");
    userInput.value = "";

    const typingMsg = appendMessage("Digitando...", "bot-message");
    typingMsg.classList.add("typing");

    setLoading(true);

    try {
      const resposta = await enviarParaAPI(text);
      typingMsg.remove();
      appendMessage(resposta || "Sem resposta no momento.", "bot-message");
    } catch (err) {
      typingMsg.remove();
      appendMessage("Erro ao enviar mensagem. Verifique a API e tente novamente.", "error-message");
      console.error(err);
    } finally {
      setLoading(false);
      userInput.focus();
    }
  }

  function mostrarMensagemFermento() {
    // Mostra a pergunta do usuário no chat
    appendMessage("Calcular fermento", "user-message");

    // Bot responde pedindo as informações
    const resposta =
      "Para calcular o fermento, preciso de duas informações:\n\n" +
      "1. Quantidade de farinha (em kg)\n" +
      "2. Temperatura ambiente (em °C)\n\n" +
      "Digite assim: \"calcular fermento para 2 kg com temperatura 28 graus\"";

    appendMessage(resposta, "bot-message");
    userInput.focus();
  }

  sendBtn.addEventListener("click", () => sendMessage());

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  document.querySelectorAll(".quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const msg = btn.getAttribute("data-msg") || btn.innerText;

      // Botão de fermento: mostra instrução sem chamar a API
      if (msg.toLowerCase().includes("fermento")) {
        mostrarMensagemFermento();
        return;
      }

      sendMessage(msg);
    });
  });

  appendMessage(
    "Olá. Sou o Padaria-Bot. Posso ajudar com receitas, sugestões para dias quentes ou frios e cálculo de fermento.",
    "bot-message"
  );
});