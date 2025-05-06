const startBtn = document.getElementById('start-btn');
const messages = document.getElementById('messages');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'en-US';
recognition.interimResults = false;

startBtn.onclick = () => {
  recognition.start();
};

recognition.onresult = (event) => {
  const userInput = event.results[0][0].transcript;
  addMessage("You: " + userInput);

  fetch("/get-response", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ user_input: userInput })
  })
  .then(res => res.json())
  .then(data => {
    const aiReply = data.reply;
    addMessage("Companion: " + aiReply);
    speak(aiReply);
  });
};

function addMessage(text) {
  const msg = document.createElement('div');
  msg.textContent = text;
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
}

function speak(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  speechSynthesis.speak(utterance);
}
