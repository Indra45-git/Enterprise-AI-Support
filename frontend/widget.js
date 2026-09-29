/**
 * Enterprise AI Support - Embeddable Chat Widget
 * Embed on ANY website with:
 * <script src="https://your-app.vercel.app/widget.js" data-bot-id="default" data-api-url="https://your-app.vercel.app"></script>
 */
(function () {
  'use strict';

  // Prevent multiple initializations
  if (window.__AI_SUPPORT_WIDGET_LOADED__) return;
  window.__AI_SUPPORT_WIDGET_LOADED__ = true;

  // 1. Determine script attributes & API base
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const botId = currentScript ? (currentScript.getAttribute('data-bot-id') || 'default') : 'default';
  let apiUrl = currentScript ? currentScript.getAttribute('data-api-url') : '';
  if (!apiUrl) {
    if (currentScript && currentScript.src) {
      try {
        const urlObj = new URL(currentScript.src);
        apiUrl = urlObj.origin;
      } catch (e) {
        apiUrl = '';
      }
    } else {
      apiUrl = window.location.origin;
    }
  }

  // Session ID for conversation continuity
  let sessionId = sessionStorage.getItem(`ai_widget_sess_${botId}`);
  if (!sessionId) {
    sessionId = 'sess_' + Math.random().toString(36).substring(2, 11) + Date.now();
    sessionStorage.setItem(`ai_widget_sess_${botId}`, sessionId);
  }

  // Default Bot Config
  let botConfig = {
    bot_name: 'Apex AI Support',
    welcome_message: "Hello! 👋 I'm your AI customer support assistant. How can I assist you with your orders, returns, or questions today?",
    primary_color: '#6366f1',
    secondary_color: '#4f46e5',
    avatar_icon: '🤖',
    placeholder_text: 'Ask about orders, returns, tracking, policies…',
    suggested_questions: [
      'Where is my order ORD00012?',
      'What is your return policy?',
      'Can I return an item?',
      'Open a support ticket'
    ]
  };

  let isOpen = false;
  let isSending = false;
  const messages = [];

  // 2. Inject Scoped Stylesheet
  const styleEl = document.createElement('style');
  styleEl.id = 'ai-support-widget-styles';
  styleEl.textContent = `
    #ai-support-widget-root {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      box-sizing: border-box;
      line-height: 1.5;
    }
    #ai-support-widget-root * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    /* Floating Launcher Button */
    .ai-widget-launcher {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: var(--ai-widget-primary, #6366f1);
      box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4), 0 2px 6px rgba(0, 0, 0, 0.15);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
      outline: none;
    }
    .ai-widget-launcher:hover {
      transform: scale(1.08) translateY(-2px);
      box-shadow: 0 12px 32px rgba(99, 102, 241, 0.5), 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    .ai-widget-launcher:active {
      transform: scale(0.96);
    }
    .ai-widget-launcher svg {
      transition: transform 0.3s ease;
    }
    .ai-widget-launcher.open .ai-icon-chat {
      display: none;
    }
    .ai-widget-launcher.open .ai-icon-close {
      display: block;
    }
    .ai-widget-launcher:not(.open) .ai-icon-close {
      display: none;
    }
    .ai-widget-pulse {
      position: absolute;
      top: 2px;
      right: 2px;
      width: 14px;
      height: 14px;
      background: #10b981;
      border: 2px solid #ffffff;
      border-radius: 50%;
    }

    /* Chat Window Container */
    .ai-widget-window {
      position: absolute;
      bottom: 76px;
      right: 0;
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 560px;
      max-height: calc(100vh - 110px);
      background: #0f172a;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 20px;
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5), 0 8px 24px rgba(0, 0, 0, 0.3);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      transform: scale(0.92) translateY(20px);
      pointer-events: none;
      transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .ai-widget-window.active {
      opacity: 1;
      transform: scale(1) translateY(0);
      pointer-events: auto;
    }

    /* Widget Header */
    .ai-widget-header {
      background: linear-gradient(135deg, var(--ai-widget-primary, #6366f1), var(--ai-widget-secondary, #4f46e5));
      padding: 16px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #ffffff;
    }
    .ai-widget-header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .ai-widget-avatar {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      border: 1.5px solid rgba(255, 255, 255, 0.3);
    }
    .ai-widget-title-area h4 {
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      margin: 0;
      line-height: 1.2;
    }
    .ai-widget-status {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.85);
      display: flex;
      align-items: center;
      gap: 5px;
      margin-top: 2px;
    }
    .ai-widget-status-dot {
      width: 7px;
      height: 7px;
      background: #34d399;
      border-radius: 50%;
      display: inline-block;
      box-shadow: 0 0 6px #34d399;
    }
    .ai-widget-header-actions button {
      background: rgba(255, 255, 255, 0.15);
      border: none;
      color: #ffffff;
      width: 28px;
      height: 28px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }
    .ai-widget-header-actions button:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    /* Message Area */
    .ai-widget-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #0b1120;
    }
    .ai-widget-messages::-webkit-scrollbar {
      width: 5px;
    }
    .ai-widget-messages::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 10px;
    }

    /* Message Bubbles */
    .ai-msg {
      max-width: 82%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 13.5px;
      line-height: 1.45;
      word-break: break-word;
      animation: aiFadeIn 0.25s ease;
    }
    @keyframes aiFadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .ai-msg-bot {
      align-self: flex-start;
      background: #1e293b;
      color: #f1f5f9;
      border-bottom-left-radius: 4px;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .ai-msg-bot strong {
      color: #93c5fd;
    }
    .ai-msg-user {
      align-self: flex-end;
      background: var(--ai-widget-primary, #6366f1);
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .ai-msg-blocked {
      align-self: flex-start;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
      border-bottom-left-radius: 4px;
    }

    /* Prompt Chips */
    .ai-widget-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 6px;
    }
    .ai-chip {
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #c7d2fe;
      padding: 6px 10px;
      border-radius: 12px;
      font-size: 11.5px;
      cursor: pointer;
      transition: all 0.2s ease;
      text-align: left;
    }
    .ai-chip:hover {
      background: rgba(99, 102, 241, 0.3);
      border-color: rgba(99, 102, 241, 0.6);
      transform: translateY(-1px);
      color: #ffffff;
    }

    /* Typing Dots */
    .ai-typing {
      align-self: flex-start;
      background: #1e293b;
      padding: 10px 14px;
      border-radius: 16px;
      border-bottom-left-radius: 4px;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .ai-dot {
      width: 6px;
      height: 6px;
      background: #94a3b8;
      border-radius: 50%;
      animation: aiBounce 1.4s infinite ease-in-out both;
    }
    .ai-dot:nth-child(1) { animation-delay: -0.32s; }
    .ai-dot:nth-child(2) { animation-delay: -0.16s; }
    @keyframes aiBounce {
      0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* Input Footer */
    .ai-widget-footer {
      padding: 12px 14px;
      background: #0f172a;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    .ai-widget-input-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #1e293b;
      border-radius: 12px;
      padding: 4px 6px 4px 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: border-color 0.2s;
    }
    .ai-widget-input-wrapper:focus-within {
      border-color: var(--ai-widget-primary, #6366f1);
      box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
    }
    .ai-widget-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: #f8fafc;
      font-size: 13.5px;
      padding: 6px 0;
    }
    .ai-widget-input::placeholder {
      color: #64748b;
    }
    .ai-widget-send-btn {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      background: var(--ai-widget-primary, #6366f1);
      border: none;
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s, transform 0.2s;
    }
    .ai-widget-send-btn:hover {
      transform: scale(1.05);
    }
    .ai-widget-send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .ai-widget-branding {
      font-size: 10.5px;
      color: #64748b;
      text-align: center;
      margin-top: 8px;
    }
    .ai-widget-branding a {
      color: #818cf8;
      text-decoration: none;
    }

    @media (max-width: 480px) {
      #ai-support-widget-root {
        bottom: 16px;
        right: 16px;
      }
      .ai-widget-window {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100vw;
        height: 100vh;
        max-width: 100vw;
        max-height: 100vh;
        border-radius: 0;
        border: none;
      }
    }
  `;
  document.head.appendChild(styleEl);

  // 3. Inject Widget DOM
  const root = document.createElement('div');
  root.id = 'ai-support-widget-root';
  root.innerHTML = `
    <!-- Launcher Button -->
    <button class="ai-widget-launcher" id="aiWidgetLauncher" aria-label="Open AI Customer Support">
      <span class="ai-widget-pulse"></span>
      <svg class="ai-icon-chat" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <svg class="ai-icon-close" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>

    <!-- Chat Window -->
    <div class="ai-widget-window" id="aiWidgetWindow">
      <!-- Header -->
      <div class="ai-widget-header">
        <div class="ai-widget-header-info">
          <div class="ai-widget-avatar" id="aiWidgetAvatar">🤖</div>
          <div class="ai-widget-title-area">
            <h4 id="aiWidgetName">Apex AI Support</h4>
            <div class="ai-widget-status">
              <span class="ai-widget-status-dot"></span> Online · AI Support Agent
            </div>
          </div>
        </div>
        <div class="ai-widget-header-actions">
          <button id="aiWidgetClose" title="Close chat">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div class="ai-widget-messages" id="aiWidgetMessages"></div>

      <!-- Footer -->
      <div class="ai-widget-footer">
        <div class="ai-widget-input-wrapper">
          <input type="text" class="ai-widget-input" id="aiWidgetInput" placeholder="Ask a question…" autocomplete="off" />
          <button class="ai-widget-send-btn" id="aiWidgetSend" title="Send message">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div class="ai-widget-branding">
          Powered by <a href="#" id="aiWidgetBrandLink">Enterprise AI Support</a>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(root);

  // 4. Elements
  const launcher = document.getElementById('aiWidgetLauncher');
  const windowEl = document.getElementById('aiWidgetWindow');
  const closeBtn = document.getElementById('aiWidgetClose');
  const messagesContainer = document.getElementById('aiWidgetMessages');
  const inputEl = document.getElementById('aiWidgetInput');
  const sendBtn = document.getElementById('aiWidgetSend');
  const avatarEl = document.getElementById('aiWidgetAvatar');
  const nameEl = document.getElementById('aiWidgetName');

  // 5. Update UI colors & text from config
  function applyConfig(cfg) {
    botConfig = Object.assign(botConfig, cfg);
    root.style.setProperty('--ai-widget-primary', botConfig.primary_color || '#6366f1');
    root.style.setProperty('--ai-widget-secondary', botConfig.secondary_color || '#4f46e5');

    if (avatarEl) avatarEl.textContent = botConfig.avatar_icon || '🤖';
    if (nameEl) nameEl.textContent = botConfig.bot_name || 'AI Support';
    if (inputEl) inputEl.placeholder = botConfig.placeholder_text || 'Ask a question…';

    // Show initial welcome if empty
    if (messages.length === 0) {
      renderWelcome();
    }
  }

  function renderWelcome() {
    messagesContainer.innerHTML = '';
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'ai-msg ai-msg-bot';
    welcomeDiv.innerHTML = formatMarkdown(botConfig.welcome_message);
    messagesContainer.appendChild(welcomeDiv);

    if (botConfig.suggested_questions && botConfig.suggested_questions.length) {
      const chipsDiv = document.createElement('div');
      chipsDiv.className = 'ai-widget-chips';
      botConfig.suggested_questions.forEach(q => {
        const btn = document.createElement('button');
        btn.className = 'ai-chip';
        btn.textContent = q;
        btn.onclick = () => {
          inputEl.value = q;
          sendMessage();
        };
        chipsDiv.appendChild(btn);
      });
      messagesContainer.appendChild(chipsDiv);
    }
  }

  function formatMarkdown(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^### (.+)$/gm, '<strong>$1</strong>')
      .replace(/^## (.+)$/gm, '<strong>$1</strong>')
      .replace(/^- (.+)$/gm, '<div>• $1</div>')
      .replace(/\n/g, '<br/>');
  }

  function appendMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `ai-msg ai-msg-${type}`;
    if (type === 'bot' || type === 'blocked') {
      msgDiv.innerHTML = formatMarkdown(text);
    } else {
      msgDiv.textContent = text;
    }
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    messages.push({ text, type });
  }

  function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'ai-typing';
    typing.id = 'aiWidgetTyping';
    typing.innerHTML = '<span class="ai-dot"></span><span class="ai-dot"></span><span class="ai-dot"></span>';
    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTypingIndicator() {
    const el = document.getElementById('aiWidgetTyping');
    if (el) el.remove();
  }

  // 6. Send Message Function
  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || isSending) return;

    appendMessage(text, 'user');
    inputEl.value = '';
    isSending = true;
    sendBtn.disabled = true;
    showTypingIndicator();

    try {
      const res = await fetch(`${apiUrl}/chat/public`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          bot_id: botId
        })
      });

      hideTypingIndicator();
      if (!res.ok) {
        appendMessage('Sorry, I encountered an issue connecting to the support server.', 'blocked');
      } else {
        const data = await res.json();
        appendMessage(data.reply, data.blocked ? 'blocked' : 'bot');
      }
    } catch (e) {
      hideTypingIndicator();
      appendMessage('Network connection error. Please try again shortly.', 'blocked');
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  // 7. Toggle Window
  function toggleWidget() {
    isOpen = !isOpen;
    if (isOpen) {
      launcher.classList.add('open');
      windowEl.classList.add('active');
      inputEl.focus();
    } else {
      launcher.classList.remove('open');
      windowEl.classList.remove('active');
    }
  }

  launcher.addEventListener('click', toggleWidget);
  closeBtn.addEventListener('click', toggleWidget);

  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 8. Fetch Settings from Backend
  fetch(`${apiUrl}/settings?bot_id=${encodeURIComponent(botId)}`)
    .then(r => r.json())
    .then(data => {
      applyConfig(data);
    })
    .catch(() => {
      // Use defaults if backend offline
      applyConfig(botConfig);
    });

  // Expose API for host page
  window.AIWidget = {
    open: () => { if (!isOpen) toggleWidget(); },
    close: () => { if (isOpen) toggleWidget(); },
    sendMessage: (txt) => { inputEl.value = txt; sendMessage(); },
    configure: applyConfig
  };

})();
