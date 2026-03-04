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

    if (!resp.ok) {
      let detalhe = "";
      try {
        const j = await resp.json();
        detalhe = j?.error || j?.erro || "";
      } catch (_) {}
      throw new Error(detalhe || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
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

  sendBtn.addEventListener("click", () => sendMessage());

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  document.querySelectorAll(".quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const msg = btn.getAttribute("data-msg") || btn.innerText;
      sendMessage(msg);
    });
  });

  appendMessage(
    "Olá. Sou o Padaria-Bot. Posso ajudar com receitas, sugestões para dias quentes ou frios e cálculo de fermento.",
    "bot-message"
  );
});