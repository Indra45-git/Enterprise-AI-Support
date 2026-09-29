/* ══════════════════════════════════════════════════════════
   Apex AI Support — Unified SaaS Application Controller
   ══════════════════════════════════════════════════════════ */

const API_BASE = (typeof window !== 'undefined' && window.__API_BASE__)
  ? window.__API_BASE__
  : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : ''; // Same-origin on Vercel

const TOKEN_TTL_MINUTES = 60;

let token = null;
let tokenExpiresAt = null;
let customerData = null;
let ordersCache = [];
let ticketsCache = [];
let productsCache = [];
let activeOrderFilter = 'all';
let activeTicketFilter = 'all';
let isMockWidgetOpen = false;

/* ══════════════════════════════════════════════════════════
   THEME TOGGLE
   ══════════════════════════════════════════════════════════ */
function applyTheme(mode) {
  document.documentElement.setAttribute('data-theme', mode);
  const dark = mode === 'dark';
  const sunIcon = document.getElementById('themeIconSun');
  const moonIcon = document.getElementById('themeIconMoon');
  if (sunIcon) sunIcon.style.display = dark ? 'none' : 'block';
  if (moonIcon) moonIcon.style.display = dark ? 'block' : 'none';
  localStorage.setItem('theme', mode);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

(function initTheme() {
  const saved = localStorage.getItem('theme');
  applyTheme(saved || 'dark');
})();

/* ══════════════════════════════════════════════════════════
   PAGE NAVIGATION
   ══════════════════════════════════════════════════════════ */
const PAGE_TITLES = {
  dashboard: 'Dashboard Overview',
  chat: 'AI Chat Studio',
  embed: 'Widget & Embed Studio',
  orders: 'Orders & Tracking',
  tickets: 'Support Tickets Desk',
  products: 'Product Catalog',
  policies: 'Knowledge Base & Policies'
};

function showPage(page) {
  document.querySelectorAll('.page-view').forEach(p => p.classList.remove('active'));

  const target = document.getElementById(`page-${page}`);
  if (target) {
    target.classList.add('active');
    target.style.animation = 'none';
    target.offsetHeight;
    target.style.animation = null;
  }

  // Update nav item active states
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navBtn = document.getElementById(`nav-${page}`);
  if (navBtn) navBtn.classList.add('active');

  // Update topbar title
  const titleEl = document.getElementById('pageTitleText');
  if (titleEl && PAGE_TITLES[page]) {
    titleEl.textContent = PAGE_TITLES[page];
  }

  // Lazy load data
  if (page === 'dashboard') loadDashboardData();
  if (page === 'orders') loadOrders();
  if (page === 'tickets') loadTickets();
  if (page === 'products') loadProducts();
  if (page === 'policies') loadPolicies();
  if (page === 'embed') loadBotSettings();
  if (page === 'chat') {
    setTimeout(() => document.getElementById('message')?.focus(), 250);
  }

  closeSidebar();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('open');
}

function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  sidebar.classList.remove('open');
  overlay.classList.remove('open');
}

/* ══════════════════════════════════════════════════════════
   AUTHENTICATION & AUTO-SESSION
   ══════════════════════════════════════════════════════════ */
/* ══════════════════════════════════════════════════════════
   AUTHENTICATION, SESSION IMMUTABILITY & ANTI-IDOR SECURITY
   ══════════════════════════════════════════════════════════ */
function handleUserPillClick() {
  if (token) {
    openAccountModal();
  } else {
    openLoginModal();
  }
}

async function loginWithPreset(email, password, silent = false) {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (!res.ok) {
      if (!silent) showToast(data?.detail || 'Authentication failed', 'error');
      return false;
    }

    token = data.access_token;
    tokenExpiresAt = Date.now() + TOKEN_TTL_MINUTES * 60 * 1000;
    customerData = data;

    sessionStorage.setItem('ai_support_token', token);
    sessionStorage.setItem('ai_support_cust', JSON.stringify(data));

    updateUserUI(data);
    loadDashboardData();
    if (!silent) showToast(`Authenticated as ${data.customer_name}! Multi-tenant session active.`, 'success');
    return true;
  } catch (e) {
    if (!silent) showToast('Network connection error', 'error');
    return false;
  }
}

function updateUserUI(data) {
  const sbAvatar = document.getElementById('sidebarUserAvatar');
  const sbName = document.getElementById('sidebarUserName');
  const sbTier = document.getElementById('sidebarUserTier');
  const sbBadge = document.getElementById('sidebarUserBadge');
  const tbAvatar = document.getElementById('topbarAvatar');
  const tbName = document.getElementById('topbarUserName');
  const tbTier = document.getElementById('topbarUserTier');
  const dashName = document.getElementById('dashCustomerName');

  if (data && token) {
    const fullName = data.customer_name || data.customer_id;
    const firstName = fullName.split(' ')[0];
    const initial = firstName.charAt(0).toUpperCase();
    const tier = (data.customer_tier || 'Customer') + ' Tier';

    if (sbAvatar) sbAvatar.textContent = initial;
    if (sbName) sbName.textContent = fullName;
    if (sbTier) sbTier.textContent = tier;
    if (sbBadge) sbBadge.innerHTML = '<span class="status-dot-active"></span><span>Verified</span>';

    if (tbAvatar) tbAvatar.textContent = initial;
    if (tbName) tbName.textContent = firstName;
    if (tbTier) tbTier.textContent = data.customer_tier || 'Gold';
    if (dashName) dashName.textContent = firstName;
  } else {
    // Logged out / Guest state
    if (sbAvatar) sbAvatar.textContent = '?';
    if (sbName) sbName.textContent = 'Guest / Unauthenticated';
    if (sbTier) sbTier.textContent = 'Click to Sign In';
    if (sbBadge) sbBadge.innerHTML = '<span class="status-dot-gray"></span><span>Sign In</span>';

    if (tbAvatar) tbAvatar.textContent = '?';
    if (tbName) tbName.textContent = 'Guest';
    if (tbTier) tbTier.textContent = 'Sign In';
    if (dashName) dashName.textContent = 'Guest';
  }
}

/* ── ACCOUNT & SECURITY PROFILE MODAL (Anti-IDOR) ── */
async function openAccountModal() {
  const modal = document.getElementById('accountModal');
  if (!modal) return;
  modal.style.display = 'flex';

  if (!token || !customerData) {
    closeAccountModal();
    openLoginModal();
    return;
  }

  // Pre-fill from cached customerData
  const fullName = customerData.customer_name || customerData.customer_id || 'Valued Customer';
  const initial = fullName.charAt(0).toUpperCase();
  const custId = customerData.customer_id || 'CUST00010';
  const tier = (customerData.customer_tier || 'Gold') + ' Tier';

  const avEl = document.getElementById('accModalAvatar');
  const nameEl = document.getElementById('accModalName');
  const emailEl = document.getElementById('accModalEmail');
  const tierEl = document.getElementById('accModalTier');
  const custIdEl = document.getElementById('accModalCustId');
  const secIdEl = document.getElementById('accModalSecId');

  if (avEl) avEl.textContent = initial;
  if (nameEl) nameEl.textContent = fullName;
  if (emailEl) emailEl.textContent = customerData.email || '—';
  if (tierEl) tierEl.textContent = tier;
  if (custIdEl) custIdEl.textContent = custId;
  if (secIdEl) secIdEl.textContent = custId;

  // Fetch verified /auth/me for live stats
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const me = await res.json();
      const phoneEl = document.getElementById('accModalPhone');
      const cityEl = document.getElementById('accModalCity');
      const ordersEl = document.getElementById('accModalOrders');
      const ticketsEl = document.getElementById('accModalTickets');

      if (phoneEl) phoneEl.textContent = me.phone || '+91 98765 43210';
      if (cityEl) cityEl.textContent = `${me.city || 'Bengaluru'}, ${me.state || 'India'}`;
      if (ordersEl) ordersEl.textContent = `${me.order_count ?? ordersCache.length} Orders`;
      if (ticketsEl) ticketsEl.textContent = `${me.ticket_count ?? ticketsCache.length} Tickets`;
    }
  } catch (e) {
    console.warn('Could not fetch /auth/me:', e);
  }
}

function closeAccountModal() {
  const modal = document.getElementById('accountModal');
  if (modal) modal.style.display = 'none';
}

function logout() {
  // Purge all customer tokens and cached data to prevent IDOR / session bleeding
  token = null;
  tokenExpiresAt = null;
  customerData = null;
  ordersCache = [];
  ticketsCache = [];

  sessionStorage.removeItem('ai_support_token');
  sessionStorage.removeItem('ai_support_cust');

  // Reset chat messages
  currentSessionId = (typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : ('sess_' + Date.now());
  const chatMessages = document.getElementById('chatMessages');
  if (chatMessages) {
    chatMessages.innerHTML = `
      <div class="chat-system-banner">
        <span>🔒 Zero-Trust Protection: Previous session terminated. Sign in to access customer orders and private records.</span>
      </div>
    `;
  }

  updateUserUI(null);
  closeAccountModal();
  showToast('Logged out successfully. Cryptographic session destroyed.', 'info');
  openLoginModal();
}

/* ── SIGN IN MODAL ── */
function openLoginModal() {
  const modal = document.getElementById('loginModal');
  if (!modal) return;
  modal.style.display = 'flex';
  const statusEl = document.getElementById('loginFormStatus');
  if (statusEl) {
    statusEl.textContent = '';
    statusEl.className = 'login-status';
  }
  loadDemoCustomers();
}

function closeLoginModal() {
  const modal = document.getElementById('loginModal');
  if (modal) modal.style.display = 'none';
}

async function handleLoginSubmit() {
  const emailInput = document.getElementById('loginEmail');
  const passInput = document.getElementById('loginPassword');
  const statusEl = document.getElementById('loginFormStatus');
  const btn = document.getElementById('loginSubmitBtn');

  const email = emailInput?.value.trim();
  const password = passInput?.value.trim();

  if (!email || !password) {
    if (statusEl) {
      statusEl.className = 'login-status error';
      statusEl.textContent = 'Please enter both email and password.';
    }
    return;
  }

  if (btn) btn.disabled = true;
  if (statusEl) {
    statusEl.className = 'login-status info';
    statusEl.textContent = 'Authenticating via secure gateway…';
  }

  try {
    const success = await loginWithPreset(email, password, true);
    if (success) {
      closeLoginModal();
      showToast(`Welcome back, ${customerData.customer_name}! Session bound.`, 'success');
      showPage('dashboard');
    } else {
      if (statusEl) {
        statusEl.className = 'login-status error';
        statusEl.textContent = 'Invalid credentials. Please verify email and password.';
      }
    }
  } catch (e) {
    if (statusEl) {
      statusEl.className = 'login-status error';
      statusEl.textContent = 'Network error during sign in.';
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

function fillLoginCredentials(email, password = 'demo1234') {
  const emailInput = document.getElementById('loginEmail');
  const passInput = document.getElementById('loginPassword');
  if (emailInput) emailInput.value = email;
  if (passInput) passInput.value = password;
  const statusEl = document.getElementById('loginFormStatus');
  if (statusEl) {
    statusEl.className = 'login-status info';
    statusEl.textContent = `Selected demo account for ${email}. Click Sign In to authenticate.`;
  }
}

// Demo Customers List for Sign In Helper
async function loadDemoCustomers() {
  try {
    const res = await fetch(`${API_BASE}/auth/demo-customers`);
    if (res.ok) {
      const customers = await res.json();
      renderDemoUserChips(customers);
    }
  } catch (e) {
    console.warn('Could not load demo accounts:', e);
  }
}

function renderDemoUserChips(customers) {
  const container = document.getElementById('demoUserChips');
  if (!container) return;
  container.innerHTML = customers.map(c => `
    <div class="demo-user-chip" onclick="fillLoginCredentials('${escapeHtml(c.email)}', 'demo1234')">
      <div class="chip-avatar">${escapeHtml(c.name.charAt(0))}</div>
      <div class="chip-info">
        <span class="chip-name">${escapeHtml(c.name)}</span>
        <span class="chip-tier-tag">${escapeHtml(c.customer_tier || 'Standard')}</span>
      </div>
    </div>
  `).join('');
}

/* ══════════════════════════════════════════════════════════
   DASHBOARD
   ══════════════════════════════════════════════════════════ */
async function loadDashboardData() {
  if (!token) return;

  // 1. Fetch Orders
  try {
    const ordersRes = await fetch(`${API_BASE}/orders`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (ordersRes.ok) {
      ordersCache = await ordersRes.json();
      const countEl = document.getElementById('statOrders');
      const navOrderCount = document.getElementById('navOrderCount');
      if (countEl) countEl.textContent = ordersCache.length || 0;
      if (navOrderCount) navOrderCount.textContent = ordersCache.length || 0;
      renderRecentOrders(ordersCache.slice(0, 4));
    }
  } catch (e) {
    console.error('Error fetching orders for dashboard:', e);
  }

  // 2. Fetch Tickets
  try {
    const ticketsRes = await fetch(`${API_BASE}/tickets`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (ticketsRes.ok) {
      ticketsCache = await ticketsRes.json();
      const countEl = document.getElementById('statTickets');
      const navTicketCount = document.getElementById('navTicketCount');
      if (countEl) countEl.textContent = ticketsCache.length || 0;
      if (navTicketCount) navTicketCount.textContent = ticketsCache.length || 0;
    }
  } catch (e) {
    console.error('Error fetching tickets for dashboard:', e);
  }

  // 3. Fetch Bot Settings
  try {
    const sRes = await fetch(`${API_BASE}/settings`);
    if (sRes.ok) {
      const s = await sRes.json();
      const miniName = document.getElementById('miniBotName');
      const miniAvatar = document.getElementById('miniBotAvatar');
      const miniHeader = document.getElementById('miniBotHeader');
      if (miniName) miniName.textContent = s.bot_name;
      if (miniAvatar) miniAvatar.textContent = s.avatar_icon || '🤖';
      if (miniHeader) miniHeader.style.background = s.primary_color || '#6366f1';
    }
  } catch (e) {}
}

function renderRecentOrders(orders) {
  const container = document.getElementById('dashOrdersList');
  if (!container) return;

  if (!orders || orders.length === 0) {
    container.innerHTML = '<div class="empty-loader">No orders found for this customer account.</div>';
    return;
  }

  container.innerHTML = `
    <div class="table-responsive">
      <table class="modern-table">
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Date</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${orders.map(o => `
            <tr>
              <td><span class="font-mono text-brand cursor-pointer" onclick="askAboutOrder('${o.order_id}')">${escapeHtml(o.order_id)}</span></td>
              <td>${o.order_date || '—'}</td>
              <td><strong>₹${o.total_amount?.toLocaleString() || '—'}</strong></td>
              <td><span class="status-pill status-${(o.status||'').toLowerCase()}">${escapeHtml(o.status)}</span></td>
              <td>
                <button class="btn-table-action" onclick="askAboutOrder('${o.order_id}')">
                  Ask AI 💬
                </button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function sendPresetFromDash(text) {
  showPage('chat');
  setTimeout(() => {
    document.getElementById('message').value = text;
    send();
  }, 200);
}

/* ══════════════════════════════════════════════════════════
   AI CHAT STUDIO
   ══════════════════════════════════════════════════════════ */
async function send() {
  const input = document.getElementById('message');
  const text = input.value.trim();
  if (!text) return;

  addMsg(text, 'user');
  input.value = '';
  showTyping();

  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ message: text })
    });

    const data = await res.json();
    removeTyping();

    if (!res.ok) {
      if (res.status === 401) {
        addMsg('🔴 Your session expired. Re-authenticating…', 'blocked');
        await loginWithPreset('user010@example.com', 'demo1234', true);
        return;
      }
      addMsg(data?.detail || data?.message || `Error ${res.status}`, 'blocked');
      return;
    }

    addMsg(data.reply, data.blocked ? 'blocked' : 'bot', data.tool_calls);

  } catch (e) {
    removeTyping();
    addMsg('⚠️ Network error — unable to reach AI support backend.', 'blocked');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function addMsg(text, cls, toolCalls) {
  const container = document.getElementById('chatMessages');
  const welcome = document.getElementById('chatWelcome');
  if (welcome) welcome.style.display = 'none';

  const div = document.createElement('div');
  div.className = `chat-bubble-row ${cls === 'user' ? 'row-user' : 'row-bot'}`;

  let toolPills = '';
  if (toolCalls && toolCalls.length) {
    toolPills = `<div class="msg-tools-row">${toolCalls.map(t => `<span class="tool-tag">⚙️ ${escapeHtml(t)}</span>`).join('')}</div>`;
  }

  const avatar = cls === 'user' ? (customerData?.customer_name?.charAt(0) || 'U') : '🤖';
  const avatarClass = cls === 'user' ? 'avatar-user' : 'avatar-bot';

  div.innerHTML = `
    <div class="msg-avatar ${avatarClass}">${avatar}</div>
    <div class="msg-bubble ${cls}">
      ${toolPills}
      <div class="msg-text">${cls === 'bot' || cls === 'blocked' ? simpleMarkdown(text || '—') : escapeHtml(text || '—')}</div>
    </div>
  `;

  container.appendChild(div);
  scrollToBottom();
}

function showTyping() {
  const container = document.getElementById('chatMessages');
  const welcome = document.getElementById('chatWelcome');
  if (welcome) welcome.style.display = 'none';

  const div = document.createElement('div');
  div.className = 'chat-bubble-row row-bot';
  div.id = 'typingIndicator';
  div.innerHTML = `
    <div class="msg-avatar avatar-bot">🤖</div>
    <div class="msg-bubble bot typing-box">
      <div class="typing-dots-anim"><span></span><span></span><span></span></div>
      <span class="typing-label">Verifying tools & policies…</span>
    </div>
  `;
  container.appendChild(div);
  scrollToBottom();
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function scrollToBottom() {
  const chatWindow = document.getElementById('chatWindow');
  if (chatWindow) {
    requestAnimationFrame(() => {
      chatWindow.scrollTop = chatWindow.scrollHeight;
    });
  }
}

function sendPreset(text) {
  document.getElementById('message').value = text;
  send();
}

function clearChat() {
  const container = document.getElementById('chatMessages');
  if (container) container.innerHTML = '';
  const welcome = document.getElementById('chatWelcome');
  if (welcome) welcome.style.display = 'flex';
  showToast('Chat history cleared', 'info');
}

function simpleMarkdown(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
    .replace(/^---$/gm, '<hr class="md-hr"/>')
    .replace(/^- (.+)$/gm, '<div class="md-li">• $1</div>')
    .replace(/\n/g, '<br/>');
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

/* ══════════════════════════════════════════════════════════
   WIDGET & EMBED STUDIO
   ══════════════════════════════════════════════════════════ */
async function loadBotSettings() {
  try {
    const res = await fetch(`${API_BASE}/settings`);
    if (res.ok) {
      const data = await res.json();
      populateSettingsForm(data);
      updatePreviewFromForm();
      generateEmbedScript();
    }
  } catch (e) {
    console.error('Error fetching bot settings:', e);
  }
}

function populateSettingsForm(data) {
  if (data.bot_name) document.getElementById('customBotName').value = data.bot_name;
  if (data.welcome_message) document.getElementById('customWelcomeMsg').value = data.welcome_message;
  if (data.primary_color) {
    document.getElementById('customPrimaryColor').value = data.primary_color;
    document.getElementById('primaryColorHex').textContent = data.primary_color;
  }
  if (data.avatar_icon) document.getElementById('customAvatar').value = data.avatar_icon;
  if (data.placeholder_text) document.getElementById('customPlaceholder').value = data.placeholder_text;
  if (data.suggested_questions_raw) document.getElementById('customQuestions').value = data.suggested_questions_raw;
}

function updatePreviewFromForm() {
  const name = document.getElementById('customBotName')?.value || 'Apex AI Support';
  const welcome = document.getElementById('customWelcomeMsg')?.value || 'Hello! How can I help you?';
  const color = document.getElementById('customPrimaryColor')?.value || '#6366f1';
  const avatar = document.getElementById('customAvatar')?.value || '🤖';
  const questionsRaw = document.getElementById('customQuestions')?.value || '';

  const hexLabel = document.getElementById('primaryColorHex');
  if (hexLabel) hexLabel.textContent = color;

  // 1. Update Preview Mock Inside the Studio Frame
  const mockHeader = document.getElementById('mockChatHeader');
  if (mockHeader) mockHeader.style.background = color;

  const mockLauncher = document.getElementById('mockLauncher');
  if (mockLauncher) mockLauncher.style.background = color;

  const mockName = document.getElementById('mockName');
  if (mockName) mockName.textContent = name;

  const mockAvatar = document.getElementById('mockAvatar');
  if (mockAvatar) mockAvatar.textContent = avatar;

  const mockWelcome = document.getElementById('mockWelcomeMsg');
  if (mockWelcome) mockWelcome.textContent = welcome;

  const chipsContainer = document.getElementById('mockChipsContainer');
  if (chipsContainer && questionsRaw) {
    const questions = questionsRaw.split('|').map(q => q.trim()).filter(Boolean);
    chipsContainer.innerHTML = questions.map(q => `
      <button class="sim-chip" onclick="simulateMockChat('${escapeHtml(q)}')">${escapeHtml(q)}</button>
    `).join('');
  }

  // 2. Real-time Sync with the actual live floating widget on the screen!
  if (window.AIWidget && typeof window.AIWidget.configure === 'function') {
    const questions = questionsRaw.split('|').map(q => q.trim()).filter(Boolean);
    window.AIWidget.configure({
      bot_name: name,
      welcome_message: welcome,
      primary_color: color,
      avatar_icon: avatar,
      suggested_questions: questions
    });
  }

  // 3. Update Chat Studio labels
  const chatStudioBotName = document.getElementById('chatStudioBotName');
  const chatStudioAvatar = document.getElementById('chatStudioAvatar');
  if (chatStudioBotName) chatStudioBotName.textContent = name;
  if (chatStudioAvatar) chatStudioAvatar.textContent = avatar;

  generateEmbedScript();
}

function applyColorPreset(primary, secondary) {
  document.getElementById('customPrimaryColor').value = primary;
  document.getElementById('primaryColorHex').textContent = primary;
  updatePreviewFromForm();
}

async function saveBotSettings() {
  const bot_name = document.getElementById('customBotName').value.trim();
  const welcome_message = document.getElementById('customWelcomeMsg').value.trim();
  const primary_color = document.getElementById('customPrimaryColor').value;
  const avatar_icon = document.getElementById('customAvatar').value;
  const placeholder_text = document.getElementById('customPlaceholder').value.trim();
  const suggested_questions = document.getElementById('customQuestions').value.trim();

  const statusEl = document.getElementById('settingsStatus');
  const btn = document.getElementById('saveSettingsBtn');
  btn.disabled = true;
  statusEl.className = 'login-status';
  statusEl.textContent = 'Saving configuration…';

  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bot_name,
        welcome_message,
        primary_color,
        avatar_icon,
        placeholder_text,
        suggested_questions,
      })
    });

    if (res.ok) {
      statusEl.className = 'login-status success';
      statusEl.textContent = '✓ Saved successfully!';
      showToast('Chatbot settings updated & synchronized!', 'success');
      loadDashboardData();
    } else {
      statusEl.className = 'login-status error';
      statusEl.textContent = 'Failed to save settings.';
    }
  } catch (e) {
    statusEl.className = 'login-status error';
    statusEl.textContent = 'Network error saving settings.';
  } finally {
    btn.disabled = false;
  }
}

async function resetBotSettings() {
  if (!confirm('Reset chatbot configuration to default?')) return;
  try {
    const res = await fetch(`${API_BASE}/settings/reset`, { method: 'POST' });
    if (res.ok) {
      loadBotSettings();
      showToast('Settings reset to default', 'info');
    }
  } catch (e) {}
}

function generateEmbedScript() {
  const origin = window.location.origin;
  const scriptTag = `<!-- Enterprise AI Support Chatbot Widget -->\n<script src="${origin}/widget.js" data-bot-id="default" data-api-url="${origin}"></script>`;
  const codeEl = document.getElementById('embedScriptCode');
  if (codeEl) codeEl.textContent = scriptTag;
}

function copyEmbedScript() {
  const codeEl = document.getElementById('embedScriptCode');
  const text = codeEl ? codeEl.textContent : `<script src="${window.location.origin}/widget.js" data-bot-id="default"></script>`;
  navigator.clipboard.writeText(text).then(() => {
    const btnText = document.getElementById('copyBtnText');
    if (btnText) btnText.textContent = 'Copied to Clipboard! ✓';
    showToast('Embed code copied! Ready to paste into any website.', 'success');
    setTimeout(() => {
      if (btnText) btnText.textContent = 'Copy Embed Code';
    }, 2500);
  });
}

// Studio Device Mockup Controls
function toggleMockWidget() {
  const win = document.getElementById('mockChatWindow');
  const launcher = document.getElementById('mockLauncher');
  isMockWidgetOpen = !isMockWidgetOpen;
  if (win) win.classList.toggle('active', isMockWidgetOpen);
  if (launcher) launcher.classList.toggle('open', isMockWidgetOpen);
}

async function simulateMockSend() {
  const input = document.getElementById('mockInput');
  const text = input?.value.trim();
  if (!text) return;
  input.value = '';
  await simulateMockChat(text);
}

async function simulateMockChat(text) {
  const body = document.getElementById('mockChatBody');
  if (!body) return;

  const userDiv = document.createElement('div');
  userDiv.className = 'sim-msg sim-msg-user';
  userDiv.textContent = text;
  body.appendChild(userDiv);
  body.scrollTop = body.scrollHeight;

  const typingDiv = document.createElement('div');
  typingDiv.className = 'sim-typing';
  typingDiv.innerHTML = '<span></span><span></span><span></span>';
  body.appendChild(typingDiv);
  body.scrollTop = body.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/chat/public`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    typingDiv.remove();

    if (res.ok) {
      const data = await res.json();
      const botDiv = document.createElement('div');
      botDiv.className = `sim-msg ${data.blocked ? 'sim-msg-blocked' : 'sim-msg-bot'}`;
      botDiv.innerHTML = simpleMarkdown(data.reply);
      body.appendChild(botDiv);
    }
  } catch (e) {
    typingDiv.remove();
  }
  body.scrollTop = body.scrollHeight;
}

/* ══════════════════════════════════════════════════════════
   ORDERS & TRACKING
   ══════════════════════════════════════════════════════════ */
async function loadOrders() {
  const grid = document.getElementById('ordersGrid');
  grid.innerHTML = '<div class="empty-loader">Loading verified orders…</div>';

  try {
    const res = await fetch(`${API_BASE}/orders`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!res.ok) {
      grid.innerHTML = '<div class="empty-loader">Failed to load orders.</div>';
      return;
    }

    ordersCache = await res.json();
    renderFilteredOrders();
  } catch (e) {
    grid.innerHTML = '<div class="empty-loader">Network error loading orders.</div>';
  }
}

function setOrderFilter(filter) {
  activeOrderFilter = filter;
  document.querySelectorAll('#page-orders .f-tab').forEach(b => {
    b.classList.toggle('active', b.textContent.toLowerCase().includes(filter.toLowerCase()) || (filter === 'all' && b.textContent.includes('All')));
  });
  renderFilteredOrders();
}

function filterOrders() {
  renderFilteredOrders();
}

function renderFilteredOrders() {
  const grid = document.getElementById('ordersGrid');
  const term = document.getElementById('orderSearchInput')?.value.trim().toLowerCase() || '';

  let list = ordersCache || [];
  if (activeOrderFilter !== 'all') {
    list = list.filter(o => (o.status || '').toLowerCase() === activeOrderFilter.toLowerCase());
  }
  if (term) {
    list = list.filter(o => o.order_id.toLowerCase().includes(term) || (o.tracking_number && o.tracking_number.toLowerCase().includes(term)));
  }

  if (!list.length) {
    grid.innerHTML = '<div class="empty-loader">No orders match this filter.</div>';
    return;
  }

  grid.innerHTML = list.map(order => {
    const items = order.items || [];
    return `
      <div class="order-entry-card" onclick="askAboutOrder('${order.order_id}')">
        <div class="order-top-row">
          <div>
            <span class="order-code font-mono">${escapeHtml(order.order_id)}</span>
            <span class="order-date-label">Placed on ${order.order_date || 'Recently'}</span>
          </div>
          <span class="status-pill status-${(order.status||'').toLowerCase()}">${escapeHtml(order.status)}</span>
        </div>
        <div class="order-metrics-row">
          <div class="m-col">
            <span class="m-label">Amount</span>
            <strong class="m-val text-brand">₹${order.total_amount?.toLocaleString() || '—'}</strong>
          </div>
          <div class="m-col">
            <span class="m-label">Payment</span>
            <strong class="m-val">${escapeHtml(order.payment_status || 'Paid')}</strong>
          </div>
          ${order.tracking_number ? `
            <div class="m-col">
              <span class="m-label">Courier Tracking</span>
              <strong class="m-val font-mono">${escapeHtml(order.tracking_number)}</strong>
            </div>
          ` : ''}
        </div>
        ${items.length ? `
          <div class="items-list-box">
            <span class="items-heading">Items:</span>
            ${items.map(i => `<span class="item-tag">${escapeHtml(i.product_name || i.product_id)}${i.quantity > 1 ? ` ×${i.quantity}` : ''}</span>`).join('')}
          </div>
        ` : ''}
        <div class="order-bottom-actions">
          <button class="btn-ghost btn-xs" onclick="event.stopPropagation(); askAboutOrder('${order.order_id}')">
            Ask AI About Order 💬
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function askAboutOrder(orderId) {
  showPage('chat');
  setTimeout(() => {
    document.getElementById('message').value = `Where is my order ${orderId}?`;
    send();
  }, 200);
}

/* ══════════════════════════════════════════════════════════
   SUPPORT TICKETS
   ══════════════════════════════════════════════════════════ */
async function loadTickets() {
  const stack = document.getElementById('ticketsList');
  stack.innerHTML = '<div class="empty-loader">Loading tickets…</div>';

  try {
    const res = await fetch(`${API_BASE}/tickets`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!res.ok) {
      stack.innerHTML = '<div class="empty-loader">Failed to load tickets.</div>';
      return;
    }

    ticketsCache = await res.json();
    renderFilteredTickets();
  } catch (e) {
    stack.innerHTML = '<div class="empty-loader">Network error loading tickets.</div>';
  }
}

function setTicketFilter(filter) {
  activeTicketFilter = filter;
  document.querySelectorAll('#page-tickets .f-tab').forEach(b => {
    b.classList.toggle('active', b.textContent.toLowerCase().includes(filter.toLowerCase()) || (filter === 'all' && b.textContent.includes('All')));
  });
  renderFilteredTickets();
}

function renderFilteredTickets() {
  const stack = document.getElementById('ticketsList');
  let list = ticketsCache || [];

  if (activeTicketFilter !== 'all') {
    list = list.filter(t => (t.status || '').toLowerCase() === activeTicketFilter.toLowerCase());
  }

  if (!list.length) {
    stack.innerHTML = `
      <div class="empty-loader">
        <p>No support tickets in this view.</p>
        <button class="btn-primary btn-sm" style="margin-top:12px" onclick="openNewTicketModal()">+ Create New Ticket</button>
      </div>
    `;
    return;
  }

  stack.innerHTML = list.map(t => `
    <div class="ticket-row-card">
      <div class="ticket-top-line">
        <div class="ticket-id-group">
          <span class="ticket-badge-id font-mono">${escapeHtml(t.ticket_id)}</span>
          <strong>${escapeHtml(t.issue_type || 'Support Request')}</strong>
        </div>
        <div class="ticket-pill-group">
          <span class="priority-tag priority-${(t.priority || 'medium').toLowerCase()}">${t.priority || 'Medium'}</span>
          <span class="status-pill status-${(t.status||'').toLowerCase()}">${t.status}</span>
        </div>
      </div>
      <p class="ticket-body-text">${escapeHtml(t.description || 'No description provided')}</p>
      <div class="ticket-meta-line">
        <span>Created: ${t.created_at || 'Recently'}</span>
        ${t.order_id ? `<span>Order: <strong>${t.order_id}</strong></span>` : ''}
        ${t.assigned_to ? `<span>Assigned to: <strong>${t.assigned_to}</strong></span>` : ''}
        ${(t.status || '').toLowerCase() === 'open' ? `
          <button class="btn-ghost btn-xs btn-escalate" onclick="openEscalateModal('${t.ticket_id}')">
            ⚡ Escalate to Supervisor
          </button>
        ` : ''}
      </div>
      ${t.escalation_reason ? `
        <div class="escalation-alert-box">
          <strong>Supervisor Escalation Reason:</strong> ${escapeHtml(t.escalation_reason)}
        </div>
      ` : ''}
    </div>
  `).join('');
}

function openNewTicketModal() {
  document.getElementById('newTicketModal').style.display = 'flex';
  document.getElementById('ticketModalStatus').textContent = '';
}

function closeNewTicketModal() {
  document.getElementById('newTicketModal').style.display = 'none';
}

async function submitNewTicket() {
  const issue_type = document.getElementById('ticketIssueType').value;
  const rawOrder = document.getElementById('ticketOrderId').value.trim();
  const order_id = rawOrder ? rawOrder.toUpperCase() : null;
  const description = document.getElementById('ticketDescription').value.trim();

  const statusEl = document.getElementById('ticketModalStatus');
  const btn = document.getElementById('submitTicketBtn');

  btn.disabled = true;
  statusEl.className = 'login-status';
  statusEl.textContent = 'Submitting ticket…';

  try {
    const res = await fetch(`${API_BASE}/tickets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ issue_type, order_id, description })
    });

    const data = await res.json();
    if (res.ok) {
      showToast('Support ticket created successfully!', 'success');
      closeNewTicketModal();
      loadTickets();
      loadDashboardData();
    } else {
      statusEl.className = 'login-status error';
      statusEl.textContent = data?.detail || 'Failed to create ticket';
    }
  } catch (e) {
    statusEl.className = 'login-status error';
    statusEl.textContent = 'Network error submitting ticket';
  } finally {
    btn.disabled = false;
  }
}

function openEscalateModal(ticketId) {
  document.getElementById('escalateTicketId').value = ticketId;
  document.getElementById('escalateReason').value = '';
  document.getElementById('escalateModalStatus').textContent = '';
  document.getElementById('escalateTicketModal').style.display = 'flex';
}

function closeEscalateModal() {
  document.getElementById('escalateTicketModal').style.display = 'none';
}

async function submitEscalateTicket() {
  const ticketId = document.getElementById('escalateTicketId').value;
  const reason = document.getElementById('escalateReason').value.trim();
  const statusEl = document.getElementById('escalateModalStatus');
  const btn = document.getElementById('submitEscalateBtn');

  btn.disabled = true;
  statusEl.className = 'login-status';
  statusEl.textContent = 'Escalating ticket to supervisor queue…';

  try {
    const res = await fetch(`${API_BASE}/tickets/${ticketId}/escalate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ reason })
    });

    if (res.ok) {
      showToast(`Ticket ${ticketId} escalated to human supervisor queue!`, 'success');
      closeEscalateModal();
      loadTickets();
    } else {
      const data = await res.json();
      statusEl.className = 'login-status error';
      statusEl.textContent = data?.detail || 'Escalation failed';
    }
  } catch (e) {
    statusEl.className = 'login-status error';
    statusEl.textContent = 'Network error escalating ticket';
  } finally {
    btn.disabled = false;
  }
}

/* ══════════════════════════════════════════════════════════
   PRODUCTS CATALOG
   ══════════════════════════════════════════════════════════ */
async function loadProducts() {
  const grid = document.getElementById('productsGrid');
  grid.innerHTML = '<div class="empty-loader">Loading catalog…</div>';

  try {
    const res = await fetch(`${API_BASE}/products`);
    if (res.ok) {
      productsCache = await res.json();
      renderProducts();
    }
  } catch (e) {
    grid.innerHTML = '<div class="empty-loader">Network error loading products.</div>';
  }
}

function filterProducts() {
  renderProducts();
}

function renderProducts() {
  const grid = document.getElementById('productsGrid');
  const term = document.getElementById('productSearchInput')?.value.trim().toLowerCase() || '';

  let list = productsCache || [];
  if (term) {
    list = list.filter(p => p.product_name.toLowerCase().includes(term) || p.product_id.toLowerCase().includes(term) || (p.category && p.category.toLowerCase().includes(term)));
  }

  if (!list.length) {
    grid.innerHTML = '<div class="empty-loader">No products found.</div>';
    return;
  }

  grid.innerHTML = list.map(p => `
    <div class="product-item-card">
      <div class="product-top">
        <span class="product-sku font-mono">${p.product_id}</span>
        <span class="product-category-chip">${escapeHtml(p.category || 'Hardware')}</span>
      </div>
      <h4 class="product-title">${escapeHtml(p.product_name)}</h4>
      <div class="product-specs">
        <span>Stock: <strong>${p.stock_quantity ?? '—'} units</strong></span>
        <span>Warranty: <strong>${p.warranty_months ? `${p.warranty_months} mo` : 'Standard'}</strong></span>
        <span>Returnable: <strong>${p.returnable ? 'Yes ✓' : 'No ✗'}</strong></span>
      </div>
      <div class="product-card-bottom">
        <span class="product-price-val">₹${p.price?.toLocaleString() || '—'}</span>
        <button class="btn-ghost btn-xs" onclick="askAboutProduct('${p.product_id}')">Ask AI 💬</button>
      </div>
    </div>
  `).join('');
}

function askAboutProduct(prodId) {
  showPage('chat');
  setTimeout(() => {
    document.getElementById('message').value = `Tell me about product ${prodId}`;
    send();
  }, 200);
}

/* ══════════════════════════════════════════════════════════
   POLICIES & KNOWLEDGE BASE (RAG Ground-Truth Governance)
   ══════════════════════════════════════════════════════════ */
let policiesCache = [];
let activePolicyCategory = 'all';
let currentViewingPolicy = null;

const DEFAULT_POLICIES = [
  {
    filename: 'return_policy.md',
    title: 'Enterprise Return Policy',
    category: 'returns',
    badge: '10-Day Window',
    icon: '📦',
    summary: 'Customers may initiate a return for any eligible item within 10 calendar days of verified carrier delivery. Packaging must be intact with all barcodes and serials intact.',
    prompt: 'What is the return policy window and eligibility criteria?'
  },
  {
    filename: 'refund_policy.md',
    title: 'Automated Refund Policy',
    category: 'refunds',
    badge: '3-5 Business Days',
    icon: '💳',
    summary: 'Refunds are automatically issued to original payment methods (UPI, Card, Netbanking) within 3 to 5 business days after warehouse inspection and approval.',
    prompt: 'How long do refunds take and what payment methods receive them?'
  },
  {
    filename: 'shipping_policy.md',
    title: 'Shipping & Fulfillment SLA',
    category: 'shipping',
    badge: 'Standard & Express',
    icon: '🚚',
    summary: 'Standard courier delivery completes in 3-5 business days; Express delivery delivers in 1-2 business days. Real-time courier tracking is provided via BlueDart and Delhivery.',
    prompt: 'What are the delivery times for shipping?'
  },
  {
    filename: 'cancellation_policy.md',
    title: 'Order Cancellation Policy',
    category: 'cancellations',
    badge: 'Pre-Dispatch Only',
    icon: '🚫',
    summary: 'Orders can only be cancelled while status is "Processing". Once order status changes to "Shipped", cancellation is locked and return procedure applies.',
    prompt: 'Can I cancel an order that has already shipped?'
  },
  {
    filename: 'warranty_policy.md',
    title: 'Manufacturer Warranty Policy',
    category: 'warranty',
    badge: '12-24 Months',
    icon: '🛡️',
    summary: 'Hardware items carry 12 to 24 months manufacturer warranty covering functional defects, motherboard failure, and battery faults.',
    prompt: 'What does the warranty cover on electronic products?'
  },
  {
    filename: 'support_sla.md',
    title: 'Support Escalation & SLA Matrix',
    category: 'sla',
    badge: 'Tier 1 < 2s · Tier 2 < 3h',
    icon: '⚡',
    summary: 'AI first-response in under 2 seconds. Tier 2 human supervisor escalation response within 3 hours. Critical billing issues escalated automatically to priority queue.',
    prompt: 'What are your support response times and SLA?'
  },
  {
    filename: 'product_faq.md',
    title: 'Product Catalog & Invoicing FAQ',
    category: 'faq',
    badge: 'Verified FAQ',
    icon: '❓',
    summary: 'Frequently asked questions regarding GST tax invoices, serial number verification, enterprise licensing, and payment gateways.',
    prompt: 'Where can I download invoices and tax receipts?'
  }
];

async function loadPolicies() {
  const grid = document.getElementById('policiesGrid');
  if (grid && !policiesCache.length) {
    grid.innerHTML = '<div class="empty-loader">Loading verified enterprise policy documents…</div>';
  }

  try {
    const res = await fetch(`${API_BASE}/policies`);
    if (res.ok) {
      policiesCache = await res.json();
    } else {
      policiesCache = DEFAULT_POLICIES;
    }
  } catch (e) {
    policiesCache = DEFAULT_POLICIES;
  }

  renderPolicies();
  initReturnCalc();
}

function setPolicyCategory(cat) {
  activePolicyCategory = cat;
  document.querySelectorAll('#policyCategoryTabs .policy-tab').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-cat') === cat);
  });
  renderPolicies();
}

function filterPolicies() {
  const input = document.getElementById('policySearchInput');
  const clearBtn = document.getElementById('clearPolicySearchBtn');
  if (clearBtn) {
    clearBtn.style.display = input?.value ? 'inline-block' : 'none';
  }
  renderPolicies();
}

function clearPolicySearch() {
  const input = document.getElementById('policySearchInput');
  if (input) input.value = '';
  const clearBtn = document.getElementById('clearPolicySearchBtn');
  if (clearBtn) clearBtn.style.display = 'none';
  renderPolicies();
}

function renderPolicies() {
  const grid = document.getElementById('policiesGrid');
  if (!grid) return;

  const query = document.getElementById('policySearchInput')?.value.trim().toLowerCase() || '';
  let list = policiesCache.length ? policiesCache : DEFAULT_POLICIES;

  if (activePolicyCategory !== 'all') {
    list = list.filter(p => p.category === activePolicyCategory);
  }

  if (query) {
    list = list.filter(p =>
      p.title.toLowerCase().includes(query) ||
      (p.summary && p.summary.toLowerCase().includes(query)) ||
      (p.content && p.content.toLowerCase().includes(query)) ||
      (p.badge && p.badge.toLowerCase().includes(query)) ||
      (p.filename && p.filename.toLowerCase().includes(query))
    );
  }

  // Update counters
  const counterEl = document.getElementById('policyMatchCounter');
  if (counterEl) {
    counterEl.textContent = `Showing ${list.length} of ${policiesCache.length || DEFAULT_POLICIES.length} Policies`;
  }
  const pillEl = document.getElementById('policyCountPill');
  if (pillEl) {
    pillEl.textContent = `${policiesCache.length || DEFAULT_POLICIES.length} Verified Policies Active`;
  }

  if (!list.length) {
    grid.innerHTML = `
      <div class="empty-state-box" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
        <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
        <h4>No policies match your search</h4>
        <p class="text-tertiary">Try clearing your search query or switching categories.</p>
        <button class="btn-secondary btn-sm" onclick="clearPolicySearch(); setPolicyCategory('all')">Reset Search</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = list.map(p => `
    <div class="policy-doc-card">
      <div class="p-card-top">
        <div class="p-card-header-left">
          <span class="p-card-icon">${p.icon || '📄'}</span>
          <h4 class="p-card-title">${escapeHtml(p.title)}</h4>
        </div>
        <span class="p-card-badge">${escapeHtml(p.badge || 'Policy')}</span>
      </div>

      <p class="p-card-summary">${escapeHtml(p.summary)}</p>

      <div class="p-card-meta-row">
        <span class="p-card-source font-mono">knowledge_base/${escapeHtml(p.filename)}</span>
        <span class="chip-tier-tag">${escapeHtml(p.category || 'Rules')}</span>
      </div>

      <div class="p-card-actions-bar">
        <button class="btn-secondary btn-xs" onclick="openPolicyModal('${escapeHtml(p.filename)}')">
          📖 Read Full Document
        </button>
        <button class="btn-primary btn-xs" onclick="sendPresetFromDash('${escapeHtml(p.prompt)}')">
          Ask AI 💬
        </button>
      </div>
    </div>
  `).join('');
}

function openPolicyModal(filename) {
  const modal = document.getElementById('policyDetailModal');
  if (!modal) return;

  const doc = (policiesCache.length ? policiesCache : DEFAULT_POLICIES).find(p => p.filename === filename);
  if (!doc) return;

  currentViewingPolicy = doc;
  document.getElementById('policyModalTitle').textContent = doc.title;
  document.getElementById('policyModalBadge').textContent = doc.badge;
  document.getElementById('policyModalFilename').textContent = `knowledge_base/${doc.filename}`;

  const bodyEl = document.getElementById('policyModalBody');
  const content = doc.content || doc.summary || 'Policy details available in support portal.';
  bodyEl.innerHTML = renderMarkdown(content);

  modal.style.display = 'flex';
}

function closePolicyModal() {
  const modal = document.getElementById('policyDetailModal');
  if (modal) modal.style.display = 'none';
  currentViewingPolicy = null;
}

function queryAiFromPolicyModal() {
  if (!currentViewingPolicy) return;
  const prompt = currentViewingPolicy.prompt || `What are the details of ${currentViewingPolicy.title}?`;
  closePolicyModal();
  sendPresetFromDash(prompt);
}

function renderMarkdown(md) {
  if (!md) return '';
  return md
    .replace(/^### (.*$)/gim, '<h5>$1</h5>')
    .replace(/^## (.*$)/gim, '<h4>$1</h4>')
    .replace(/^# (.*$)/gim, '<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code class="font-mono">$1</code>')
    .replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>')
    .replace(/^\s*\d+\.\s+(.*$)/gim, '<li>$1</li>')
    .replace(/<li>.*<\/li>/gis, (match) => `<ul>${match}</ul>`)
    .split('\n\n')
    .map(p => {
      const trimmed = p.trim();
      if (!trimmed) return '';
      if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol')) return trimmed;
      return `<p>${trimmed.replace(/\n/g, '<br/>')}</p>`;
    })
    .join('');
}

/* ── RETURN WINDOW ELIGIBILITY CALCULATOR ── */
function initReturnCalc() {
  const dateInput = document.getElementById('calcDeliveryDate');
  if (dateInput && !dateInput.value) {
    const d = new Date();
    d.setDate(d.getDate() - 3);
    dateInput.value = d.toISOString().split('T')[0];
  }
  runReturnCalc();
}

function resetReturnCalc() {
  const dateInput = document.getElementById('calcDeliveryDate');
  const condInput = document.getElementById('calcItemCondition');
  const catInput = document.getElementById('calcProductCategory');

  if (dateInput) {
    const d = new Date();
    d.setDate(d.getDate() - 3);
    dateInput.value = d.toISOString().split('T')[0];
  }
  if (condInput) condInput.value = 'unopened';
  if (catInput) catInput.value = 'standard';

  runReturnCalc();
}

function runReturnCalc() {
  const dateInput = document.getElementById('calcDeliveryDate');
  const condInput = document.getElementById('calcItemCondition');
  const catInput = document.getElementById('calcProductCategory');

  const statusEl = document.getElementById('calcResultStatus');
  const iconEl = document.getElementById('calcStatusIcon');
  const textEl = document.getElementById('calcStatusText');
  const detailEl = document.getElementById('calcResultDetail');
  const boxEl = document.getElementById('calcResultBox');
  const aiBtn = document.getElementById('calcAiActionBtn');

  if (!dateInput || !statusEl || !detailEl) return;

  const deliveryDateStr = dateInput.value;
  if (!deliveryDateStr) return;

  const deliveryDate = new Date(deliveryDateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  deliveryDate.setHours(0, 0, 0, 0);

  const diffMs = today - deliveryDate;
  const daysSinceDelivery = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const condition = condInput?.value || 'unopened';
  const category = catInput?.value || 'standard';

  const RETURN_WINDOW_DAYS = 10;
  const daysRemaining = RETURN_WINDOW_DAYS - daysSinceDelivery;

  boxEl.className = 'calc-result-box';

  if (daysSinceDelivery < 0) {
    boxEl.classList.add('calc-warning');
    if (iconEl) iconEl.textContent = '⏳';
    if (textEl) textEl.textContent = 'DELIVERY IN FUTURE / IN TRANSIT';
    detailEl.innerHTML = `Order has not been delivered yet. Return window opens on confirmed carrier delivery date. You may cancel pre-dispatch orders anytime before dispatch.`;
    if (aiBtn) aiBtn.textContent = 'Track In-Transit Order 💬';
    return;
  }

  if (category === 'software') {
    boxEl.classList.add('calc-danger');
    if (iconEl) iconEl.textContent = '❌';
    if (textEl) textEl.textContent = 'NON-RETURNABLE: DIGITAL SOFTWARE LICENSE';
    detailEl.innerHTML = `Digital licenses, downloadable software keys, and customized enterprise items are strictly <strong>non-returnable and non-refundable</strong> once generated.`;
    if (aiBtn) aiBtn.textContent = 'Ask Support About License 💬';
    return;
  }

  if (condition === 'hygiene_opened') {
    boxEl.classList.add('calc-danger');
    if (iconEl) iconEl.textContent = '⚠️';
    if (textEl) textEl.textContent = 'NON-RETURNABLE: OPENED HYGIENE ITEM';
    detailEl.innerHTML = `In-ear earphones, wearables, and personal contact items with opened security seals cannot be returned for hygiene & safety reasons. If defective, warranty service applies.`;
    if (aiBtn) aiBtn.textContent = 'Check Warranty Coverage 💬';
    return;
  }

  if (condition === 'missing_accessories') {
    boxEl.classList.add('calc-warning');
    if (iconEl) iconEl.textContent = '⚠️';
    if (textEl) textEl.textContent = 'INCOMPLETE RETURN PACKAGE';
    detailEl.innerHTML = `All original packaging, barcode serial stickers, power adapters, and bundled accessories must be returned together to pass warehouse QC inspection.`;
    if (aiBtn) aiBtn.textContent = 'Ask AI About Requirements 💬';
    return;
  }

  if (condition === 'transit_damaged') {
    boxEl.classList.add('calc-success');
    if (iconEl) iconEl.textContent = '🚨';
    if (textEl) textEl.textContent = 'PRIORITY TRANSIT DAMAGE CLAIM';
    detailEl.innerHTML = `Delivered ${daysSinceDelivery} day(s) ago. Transit damage reported within 48h qualifies for <strong>immediate free priority replacement</strong> without standard wait times.`;
    if (aiBtn) aiBtn.textContent = 'File Transit Damage Claim 💬';
    return;
  }

  if (daysSinceDelivery > RETURN_WINDOW_DAYS) {
    boxEl.classList.add('calc-expired');
    const expiredDays = daysSinceDelivery - RETURN_WINDOW_DAYS;
    if (iconEl) iconEl.textContent = '⛔';
    if (textEl) textEl.textContent = 'RETURN WINDOW EXPIRED';
    detailEl.innerHTML = `Delivered ${daysSinceDelivery} days ago. The 10-day return window expired <strong>${expiredDays} day(s) ago</strong>. Doorstep return pickup is no longer eligible. Your hardware is protected under the <strong>12 to 24 month Manufacturer Warranty</strong>.`;
    if (aiBtn) aiBtn.textContent = 'Claim Warranty Service 💬';
  } else {
    boxEl.classList.add('calc-success');
    if (iconEl) iconEl.textContent = '✅';
    if (textEl) textEl.textContent = 'ELIGIBLE FOR RETURN & FULL REFUND';
    detailEl.innerHTML = `Delivered ${daysSinceDelivery} day(s) ago. You have <strong>${daysRemaining} day(s) remaining</strong> in your guaranteed 10-day return window. Automated reverse courier pickup is 100% free.`;
    if (aiBtn) aiBtn.textContent = 'Initiate Return with AI 💬';
  }
}

function queryAiFromCalc() {
  const detail = document.getElementById('calcResultDetail')?.textContent || '';
  const prompt = `Can I return my order? ${detail}`;
  sendPresetFromDash(prompt);
}

/* ══════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
   ══════════════════════════════════════════════════════════ */
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `
    <span class="toast-dot"></span>
    <span class="toast-msg">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 250);
  }, 3000);
}

/* ══════════════════════════════════════════════════════════
   APPLICATION STARTUP
   ══════════════════════════════════════════════════════════ */
(async function init() {
  loadDemoCustomers();

  // Check saved session
  const savedToken = sessionStorage.getItem('ai_support_token');
  const savedCust = sessionStorage.getItem('ai_support_cust');

  if (savedToken && savedCust) {
    try {
      token = savedToken;
      customerData = JSON.parse(savedCust);
      tokenExpiresAt = Date.now() + TOKEN_TTL_MINUTES * 60 * 1000;
      updateUserUI(customerData);
      showPage('dashboard');
      return;
    } catch (e) {
      sessionStorage.removeItem('ai_support_token');
    }
  }

  // Auto-login with default demo customer on first boot for seamless presentation!
  await loginWithPreset('user010@example.com', 'demo1234', true);
  showPage('dashboard');
})();
