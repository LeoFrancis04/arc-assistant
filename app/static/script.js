/**
 * ARC — WebSocket chat client
 *
 * Protocol (server → client):
 *   {type: "token",       content: "..."}       streaming text chunk
 *   {type: "tool_call",   tool: "...", args: {}} tool invocation notice
 *   {type: "tool_result", tool: "...", result: "..."} tool output notice
 *   {type: "done"}                               turn complete
 *   {type: "error",       message: "..."}        failure
 */

marked.setOptions({ breaks: true, gfm: true });

// DOM refs
const messagesEl   = document.getElementById('messages');
const containerEl  = document.getElementById('messages-container');
const inputEl      = document.getElementById('message-input');
const sendBtn      = document.getElementById('send-btn');
const typingEl     = document.getElementById('typing-indicator');
const clearBtn     = document.getElementById('clear-btn');

// State
let ws              = null;
let isStreaming     = false;
let currentBubble   = null;   // active AI bubble element
let currentText     = '';     // raw markdown accumulator for live render

// ─── WebSocket ─────────────────────────────────────────────────────────────

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws/chat`);

  ws.onopen = () => {
    updateSendBtn();
  };

  ws.onmessage = (event) => {
    let data;
    try { data = JSON.parse(event.data); }
    catch { return; }
    handleMessage(data);
  };

  ws.onclose = () => {
    sendBtn.disabled = true;
    // Attempt reconnect after brief pause
    setTimeout(connect, 2000);
  };

  ws.onerror = () => ws.close();
}

// ─── Message handler ────────────────────────────────────────────────────────

function handleMessage(data) {
  switch (data.type) {

    case 'token':
      hideTyping();
      if (!currentBubble) {
        currentBubble = createAIBubble();
        currentText   = '';
      }
      currentText += data.content;
      renderMarkdown(currentBubble, currentText);
      scrollToBottom();
      break;

    case 'tool_call':
      // Close the current bubble so post-tool text gets a fresh one
      currentBubble = null;
      currentText   = '';
      hideTyping();
      appendToolIndicator(`⚡ ${data.tool}`, true);
      scrollToBottom();
      break;

    case 'tool_result':
      appendToolIndicator(`✓ ${data.tool}: ${truncate(String(data.result), 90)}`);
      showTyping();
      scrollToBottom();
      break;

    case 'done':
      isStreaming   = false;
      currentBubble = null;
      currentText   = '';
      hideTyping();
      enableInput();
      break;

    case 'error':
      hideTyping();
      appendError(data.message || 'Unknown error');
      isStreaming = false;
      enableInput();
      break;
  }
}

// ─── Send ────────────────────────────────────────────────────────────────────

function sendMessage() {
  if (isStreaming || !ws || ws.readyState !== WebSocket.OPEN) return;
  const text = inputEl.value.trim();
  if (!text) return;

  appendUserMessage(text);
  inputEl.value = '';
  resizeTextarea();
  disableInput();
  showTyping();
  scrollToBottom();

  isStreaming   = true;
  currentBubble = null;
  currentText   = '';

  ws.send(JSON.stringify({ message: text }));
}

// ─── DOM helpers ─────────────────────────────────────────────────────────────

function appendUserMessage(text) {
  const el = document.createElement('div');
  el.className = 'message user';
  el.innerHTML = `
    <div class="message-label">Leo</div>
    <div class="user-bubble">${escapeHtml(text)}</div>
  `;
  messagesEl.appendChild(el);
}

function createAIBubble() {
  const row    = document.createElement('div');
  row.className = 'message assistant';

  const label  = document.createElement('div');
  label.className = 'message-label';
  label.textContent = 'ARC';

  const bubble = document.createElement('div');
  bubble.className = 'ai-bubble';

  row.appendChild(label);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  return bubble;
}

function renderMarkdown(el, text) {
  el.innerHTML = marked.parse(text);
}

function appendToolIndicator(text, isCalling = false) {
  const el = document.createElement('div');
  el.className = 'tool-indicator' + (isCalling ? ' calling' : '');
  el.textContent = text;
  messagesEl.appendChild(el);
}

function appendError(message) {
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.innerHTML = `
    <div class="message-label" style="color:#ff6b6b">Error</div>
    <div class="ai-bubble" style="border-left-color:#ff6b6b">${escapeHtml(message)}</div>
  `;
  messagesEl.appendChild(el);
  scrollToBottom();
}

// ─── Typing indicator ────────────────────────────────────────────────────────

function showTyping() { typingEl.classList.remove('hidden'); scrollToBottom(); }
function hideTyping() { typingEl.classList.add('hidden'); }

// ─── Input state ─────────────────────────────────────────────────────────────

function disableInput() {
  inputEl.disabled = true;
  sendBtn.disabled = true;
}

function enableInput() {
  inputEl.disabled = false;
  updateSendBtn();
  inputEl.focus();
}

function updateSendBtn() {
  sendBtn.disabled =
    isStreaming ||
    inputEl.value.trim() === '' ||
    !ws ||
    ws.readyState !== WebSocket.OPEN;
}

// ─── Auto-resize textarea ────────────────────────────────────────────────────

function resizeTextarea() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
}

// ─── Scroll ──────────────────────────────────────────────────────────────────

function scrollToBottom() {
  containerEl.scrollTop = containerEl.scrollHeight;
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function truncate(str, n) {
  return str.length > n ? str.slice(0, n) + '…' : str;
}

// ─── Event listeners ─────────────────────────────────────────────────────────

inputEl.addEventListener('input', () => {
  resizeTextarea();
  updateSendBtn();
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

clearBtn.addEventListener('click', async () => {
  if (!confirm('Clear conversation history?')) return;
  await fetch('/api/clear', { method: 'POST' });
  messagesEl.innerHTML = '';
});

// ─── Init ────────────────────────────────────────────────────────────────────

connect();
 