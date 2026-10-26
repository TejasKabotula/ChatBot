// Sri Vasavi Engineering College (SVEC) - FAQ Chatbot Client JS

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const messagesStream = document.getElementById('messages-stream');
  const welcomeBanner = document.getElementById('welcome-banner');
  const statusPill = document.getElementById('system-status');

  // Check backend health
  async function checkHealth() {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        const statusText = statusPill.querySelector('.status-text');
        if (data.status === 'healthy') {
          statusText.innerHTML = 'SVEC FAQ Bot &bull; Active';
        } else {
          statusText.innerHTML = 'SVEC FAQ Bot &bull; Initializing';
        }
      }
    } catch {
      // Keep active default
    }
  }
  checkHealth();

  // Quick Prompt Chips
  document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      if (query) {
        input.value = query;
        sendMessage(query);
      }
    });
  });

  // Form submit
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    sendMessage(query);
  });

  async function sendMessage(query) {
    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;

    // Hide welcome hero on first message
    if (welcomeBanner) {
      welcomeBanner.style.display = 'none';
    }

    // Append user message
    appendUserMessage(query);

    // Append typing indicator
    const typingRow = appendTypingIndicator();
    scrollToBottom();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
      });

      // Remove typing indicator
      typingRow.remove();

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData.detail || 'Could not connect to the college server. Please try again.';
        appendBotMessage(`⚠️ ${errMsg}`, []);
      } else {
        const data = await response.json();
        appendBotMessage(data.answer, data.sources || []);
      }
    } catch (err) {
      if (typingRow) typingRow.remove();
      appendBotMessage('⚠️ Network error connecting to SVEC FAQ server. Please check your connection.', []);
    } finally {
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
      scrollToBottom();
    }
  }

  function appendUserMessage(text) {
    const timeStr = formatCurrentTime();
    const row = document.createElement('div');
    row.className = 'message-row user-row';
    row.innerHTML = `
      <div class="message-content-wrap">
        <div class="chat-bubble user-bubble">${escapeHtml(text)}</div>
        <div class="message-time">${timeStr}</div>
      </div>
      <div class="message-avatar user-avatar" title="You">You</div>
    `;
    messagesStream.appendChild(row);
  }

  function appendBotMessage(rawText, sources) {
    const timeStr = formatCurrentTime();
    const row = document.createElement('div');
    row.className = 'message-row bot-row';

    const formattedHtml = parseMarkdown(rawText);

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
      const badges = sources
        .map(src => `<span class="source-badge" title="Source: ${escapeHtml(src)}">${escapeHtml(src)}</span>`)
        .join(' ');
      sourcesHtml = `
        <div class="sources-pill-wrap">
          <span class="sources-label">Verified Sources:</span>
          ${badges}
        </div>
      `;
    }

    row.innerHTML = `
      <div class="message-avatar bot-avatar" title="SVEC FAQ Bot">
        <img src="/static/logo.png" alt="SVEC" class="bot-avatar-img" />
      </div>
      <div class="message-content-wrap">
        <div class="chat-bubble bot-bubble">
          ${formattedHtml}
          ${sourcesHtml}
        </div>
        <div class="message-time">SVEC FAQ Bot &bull; ${timeStr}</div>
      </div>
    `;
    messagesStream.appendChild(row);
  }

  function appendTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'message-row bot-row typing-row';
    row.innerHTML = `
      <div class="message-avatar bot-avatar">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9"/>
          <path d="M12 8v4l2 2"/>
        </svg>
      </div>
      <div class="message-content-wrap">
        <div class="typing-bubble">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
    `;
    messagesStream.appendChild(row);
    return row;
  }

  function scrollToBottom() {
    messagesStream.scrollTop = messagesStream.scrollHeight;
  }

  function formatCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Lightweight Markdown parser for clean response rendering
  function parseMarkdown(md) {
    if (!md) return '';

    let html = escapeHtml(md);

    // Bold text **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic text *text*
    html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');

    // Bullet points (* or -)
    const lines = html.split('\n');
    let inList = false;
    let result = [];

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();

      if (line.startsWith('* ') || line.startsWith('- ') || line.startsWith('• ')) {
        if (!inList) {
          result.push('<ul>');
          inList = true;
        }
        result.push(`<li>${line.substring(2).trim()}</li>`);
      } else if (/^\d+\.\s/.test(line)) {
        if (!inList) {
          result.push('<ol>');
          inList = true;
        }
        result.push(`<li>${line.replace(/^\d+\.\s/, '').trim()}</li>`);
      } else {
        if (inList) {
          result.push('</ul>');
          inList = false;
        }
        if (line.length > 0) {
          result.push(`<p>${line}</p>`);
        }
      }
    }
    if (inList) {
      result.push('</ul>');
    }

    return result.join('\n');
  }
});
