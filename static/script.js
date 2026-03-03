document.addEventListener("DOMContentLoaded", function () {

  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");

  if (!chatBox) {
    console.error("chat-box não encontrado");
    return;
  }

  function appendMessage(content, className) {
    const msg = document.createElement("div");
    msg.classList.add("message", className);
    msg.textContent = content;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage(text, "user-message");
    userInput.value = "";

    setTimeout(() => {
      appendMessage("Resposta simulada do Padaria-Bot.", "bot-message");
    }, 500);
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
  }

  if (userInput) {
    userInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") sendMessage();
    });
  }

  // 🔥 Mensagem inicial garantida
  appendMessage(
    " Olá. Sou o Padaria-Bot. Posso ajudar com receitas, sugestões para dias quentes ou frios e cálculo de fermentação.",
    "bot-message 🍞"
  );

});