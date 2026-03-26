/* =========================================================
   ProMat — AI Chat
   ========================================================= */

// ── State ────────────────────────────────────────────────────────────────

const activeMentions = []; // { type, id, label }
let mentionTriggerPos = -1; // textarea index where @ was typed

// ── Bootstrap ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  setupModal();
  if (SESSION_ID) initChat();
});

// ── Modal ────────────────────────────────────────────────────────────────

function setupModal() {
  const modal   = document.getElementById('new-chat-modal');
  const titleIn = document.getElementById('modal-title-input');

  function open() {
    modal.classList.remove('hidden');
    titleIn?.focus();
  }
  function close() { modal.classList.add('hidden'); }

  document.getElementById('new-chat-btn')?.addEventListener('click', open);
  document.getElementById('new-chat-btn-main')?.addEventListener('click', open);
  document.getElementById('close-modal-btn')?.addEventListener('click', close);
  document.getElementById('cancel-modal-btn')?.addEventListener('click', close);
  modal?.addEventListener('click', (e) => { if (e.target === modal) close(); });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) close();
  });
}

// ── Chat init ────────────────────────────────────────────────────────────

function initChat() {
  const form     = document.getElementById('chat-form');
  const input    = document.getElementById('message-input');
  const dropdown = document.getElementById('mention-dropdown');

  if (!form || !input) return;

  // Render existing AI messages as markdown
  document.querySelectorAll('.ai-message').forEach(el => {
    el.innerHTML = renderMarkdown(el.dataset.raw || el.textContent);
  });

  scrollToBottom();

  input.addEventListener('input', () => {
    autoResize(input);
    handleMentionInput(input);
  });

  input.addEventListener('keydown', (e) => {
    if (isDropdownOpen()) {
      handleDropdownNav(e);
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      doSend(input);
    }
  });

  document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target) && e.target !== input) hideMentionDropdown();
  });

  form.addEventListener('submit', (e) => { e.preventDefault(); doSend(input); });
}

// ── @Mention system ───────────────────────────────────────────────────────

function handleMentionInput(input) {
  const cursor = input.selectionStart;
  const slice  = input.value.slice(0, cursor);
  const match  = slice.match(/@(\S*)$/);

  if (!match) {
    hideMentionDropdown();
    mentionTriggerPos = -1;
    return;
  }

  mentionTriggerPos = slice.lastIndexOf('@');
  fetchSuggestions(match[1]);
}

function handleDropdownNav(e) {
  const items    = [...document.querySelectorAll('.mention-item')];
  const activeEl = document.querySelector('.mention-item[data-highlighted]');

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    const idx = activeEl ? items.indexOf(activeEl) : -1;
    activateItem(items[idx + 1] ?? items[0]);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    const idx = activeEl ? items.indexOf(activeEl) : items.length;
    activateItem(items[idx - 1] ?? items[items.length - 1]);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    activeEl?.click();
  } else if (e.key === 'Escape') {
    hideMentionDropdown();
  }
}

function activateItem(el) {
  document.querySelectorAll('.mention-item').forEach(i => {
    i.classList.remove('bg-gray-100', 'dark:bg-gray-700');
    delete i.dataset.highlighted;
  });
  if (el) {
    el.classList.add('bg-gray-100', 'dark:bg-gray-700');
    el.dataset.highlighted = '1';
    el.scrollIntoView({ block: 'nearest' });
  }
}

async function fetchSuggestions(query) {
  try {
    const res  = await fetch(`${MENTIONS_URL}?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    renderDropdown(data.results || []);
  } catch { hideMentionDropdown(); }
}

function renderDropdown(results) {
  const container = document.getElementById('mention-results');
  const dropdown  = document.getElementById('mention-dropdown');

  if (!results.length) { hideMentionDropdown(); return; }

  const TYPE_ICON  = { doc: 'description', project: 'folder', task: 'task_alt' };
  const TYPE_LABEL = { doc: 'Doc', project: 'Project', task: 'Task' };

  container.innerHTML = results.map((r, i) => `
    <button type="button"
      class="mention-item w-full flex items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 ${i === 0 ? 'bg-gray-100 dark:bg-gray-700' : ''}"
      ${i === 0 ? 'data-highlighted="1"' : ''}
      data-type="${r.type}" data-id="${r.id}" data-label="${escHtml(r.label)}">
      <span class="material-symbols-outlined text-base text-gray-400 flex-shrink-0">${TYPE_ICON[r.type] ?? 'label'}</span>
      <div class="flex-1 min-w-0">
        <span class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate block">${escHtml(r.label)}</span>
        <span class="text-xs text-gray-400">${TYPE_LABEL[r.type] ?? r.type} · ${escHtml(r.meta ?? '')}</span>
      </div>
    </button>`
  ).join('');

  container.querySelectorAll('.mention-item').forEach(btn => {
    btn.addEventListener('click', () =>
      selectMention(btn.dataset.type, btn.dataset.id, btn.dataset.label)
    );
  });

  dropdown.classList.remove('hidden');
}

function selectMention(type, id, label) {
  const input = document.getElementById('message-input');

  if (mentionTriggerPos !== -1) {
    const cursor = input.selectionStart;
    input.value  = input.value.slice(0, mentionTriggerPos) + input.value.slice(cursor);
    input.setSelectionRange(mentionTriggerPos, mentionTriggerPos);
  }

  addChip(type, id, label);
  hideMentionDropdown();
  mentionTriggerPos = -1;
  input.focus();
  autoResize(input);
}

function addChip(type, id, label) {
  if (activeMentions.find(m => m.type === type && String(m.id) === String(id))) return;
  activeMentions.push({ type, id, label });

  const chip = document.createElement('span');
  chip.className = 'inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20';
  chip.innerHTML = `
    <span class="material-symbols-outlined text-[11px]">${mentionIcon(type)}</span>
    ${escHtml(label)}
    <button type="button" class="ml-0.5 opacity-60 hover:opacity-100 transition-opacity leading-none" aria-label="Remove">
      <span class="material-symbols-outlined text-[11px]">close</span>
    </button>`;

  chip.querySelector('button').addEventListener('click', () => {
    const idx = activeMentions.findIndex(m => m.type === type && String(m.id) === String(id));
    if (idx !== -1) activeMentions.splice(idx, 1);
    chip.remove();
  });

  document.getElementById('mention-chips').appendChild(chip);
}

function hideMentionDropdown() {
  document.getElementById('mention-dropdown')?.classList.add('hidden');
}

function isDropdownOpen() {
  return !document.getElementById('mention-dropdown')?.classList.contains('hidden');
}

// ── Messaging ─────────────────────────────────────────────────────────────

async function doSend(input) {
  const text = input.value.trim();
  if (!text && activeMentions.length === 0) return;

  const btn = document.getElementById('send-btn');
  input.disabled = true;
  btn.disabled   = true;

  const tokens  = activeMentions.map(m => `@[${m.type}:${m.id}:${m.label}]`).join(' ');
  const fullMsg = tokens ? `${tokens} ${text}` : text;

  appendUserMessage(text, [...activeMentions]);

  input.value = '';
  activeMentions.length = 0;
  document.getElementById('mention-chips').innerHTML = '';
  autoResize(input);

  const typing = appendTyping();

  try {
    const csrf = document.querySelector('input[name="csrf_token"]')?.value
              ?? document.querySelector('meta[name="csrf-token"]')?.content;

    const res  = await fetch(MESSAGE_URL, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body:    JSON.stringify({ message: fullMsg }),
    });
    const data = await res.json();
    typing.remove();

    if (data.success) {
      appendAssistantMessage(
        data.assistant_message.content,
        data.assistant_message.citations ?? []
      );
    } else {
      appendError(data.error ?? 'Failed to get a response.');
    }
  } catch {
    typing.remove();
    appendError('Network error — please try again.');
  } finally {
    input.disabled = false;
    btn.disabled   = false;
    input.focus();
  }
}

// ── Message renderers ──────────────────────────────────────────────────────

function appendUserMessage(text, mentions) {
  const chipsHtml = mentions.length ? `
    <div class="flex flex-wrap justify-end gap-1 mt-1.5">
      ${mentions.map(m => `
        <span class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
          <span class="material-symbols-outlined text-[11px]">${mentionIcon(m.type)}</span>
          ${escHtml(m.label)}
        </span>`).join('')}
    </div>` : '';

  const wrap = document.createElement('div');
  wrap.className = 'flex justify-end';
  wrap.innerHTML = `
    <div class="max-w-[75%]">
      <div class="bg-primary text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">${escHtml(text)}</div>
      ${chipsHtml}
    </div>`;

  mountMessage(wrap);
  return wrap;
}

function appendAssistantMessage(content, citations) {
  const citationsHtml = citations.length ? `
    <div class="flex flex-wrap gap-1.5 mt-2">
      ${citations.map(c => `
        <span class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
          <span class="material-symbols-outlined text-[11px]">${mentionIcon(c.type)}</span>
          ${escHtml(c.label)}
        </span>`).join('')}
    </div>` : '';

  const wrap = document.createElement('div');
  wrap.className = 'flex gap-3';
  wrap.innerHTML = `
    <div class="w-7 h-7 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center mt-0.5">
      <span class="material-symbols-outlined text-primary text-[15px]">smart_toy</span>
    </div>
    <div class="flex-1 min-w-0 max-w-[82%]">
      <div class="ai-message text-sm text-gray-800 dark:text-gray-200 leading-relaxed">${renderMarkdown(content)}</div>
      ${citationsHtml}
    </div>`;

  mountMessage(wrap);
  return wrap;
}

function appendTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'flex gap-3';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `
    <div class="w-7 h-7 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center mt-0.5">
      <span class="material-symbols-outlined text-primary text-[15px]">smart_toy</span>
    </div>
    <div class="flex items-center gap-1 py-3">
      <span class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay:0ms"></span>
      <span class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay:150ms"></span>
      <span class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay:300ms"></span>
    </div>`;
  mountMessage(wrap);
  return wrap;
}

function appendError(msg) {
  const wrap = document.createElement('div');
  wrap.className = 'flex justify-center';
  wrap.innerHTML = `<p class="text-xs text-red-500 bg-red-50 dark:bg-red-500/10 px-3 py-1.5 rounded-full">${escHtml(msg)}</p>`;
  mountMessage(wrap);
}

function mountMessage(el) {
  const container = document.getElementById('messages');
  document.getElementById('empty-chat')?.remove();
  container.appendChild(el);
  scrollToBottom();
}

// ── Utilities ──────────────────────────────────────────────────────────────

function renderMarkdown(text) {
  if (typeof marked === 'undefined') return `<p>${escHtml(text)}</p>`;
  return marked.parse(text, { breaks: true, gfm: true });
}

function mentionIcon(type) {
  return { doc: 'description', project: 'folder', task: 'task_alt' }[type] ?? 'label';
}

function escHtml(str) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(String(str ?? '')));
  return d.innerHTML;
}

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
}

function scrollToBottom() {
  const c = document.getElementById('messages');
  if (c) c.scrollTop = c.scrollHeight;
}
