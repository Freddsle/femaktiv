(() => {
  'use strict';
  const sidebar = document.querySelector('#chat-sidebar');
  const toggle = document.querySelector('[data-toggle-sidebar]');
  const setSidebar = (open) => {
    if (!sidebar || !toggle) return;
    sidebar.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    if (open) sidebar.querySelector('button').focus();
    else toggle.focus();
  };
  toggle?.addEventListener('click', () => setSidebar(!sidebar.classList.contains('is-open')));
  document.querySelector('[data-close-sidebar]')?.addEventListener('click', () => setSidebar(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && sidebar?.classList.contains('is-open')) setSidebar(false);
  });

  const form = document.querySelector('#chat-form');
  if (!form) return;
  const input = form.querySelector('textarea');
  const sendButton = form.querySelector('[type=submit]');
  const noteInputs = [...form.querySelectorAll('[name=note_ids]')];
  const status = document.querySelector('#chat-status');
  const thread = document.querySelector('#chat-thread');
  const initialPath = window.location.pathname;
  const chatId = form.dataset.chatId;
  let pending = false;
  let navigating = false;
  let controller = null;
  let lastAttempt = null;
  const present = () => !navigating && form.isConnected && window.location.pathname === initialPath;
  const prepareNavigation = () => { navigating = true; controller?.abort(); };
  window.addEventListener('pagehide', prepareNavigation);
  window.addEventListener('pageshow', (event) => { if (event.persisted) window.location.reload(); });
  document.addEventListener('submit', (event) => {
    if (event.target !== form && !event.defaultPrevented) prepareNavigation();
  });
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || link.target === '_blank' || link.hasAttribute('download')) return;
    const destination = new URL(link.href, window.location.href);
    const sameDocument = destination.origin === window.location.origin && destination.pathname === window.location.pathname && destination.search === window.location.search;
    if (sameDocument && destination.hash) return;
    prepareNavigation();
  });
  const updateNotes = () => {
    const count = noteInputs.filter((note) => note.checked).length;
    const counter = form.querySelector('[data-attachment-count]');
    counter.textContent = String(count);
    counter.hidden = count === 0;
    noteInputs.forEach((note) => { note.disabled = pending || (!note.checked && count >= 5); });
  };
  noteInputs.forEach((note) => note.addEventListener('change', updateNotes));
  input.addEventListener('input', () => {
    form.querySelector('[data-char-count]').textContent = String(input.value.length);
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  });
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const appendMessage = (message) => {
    if ([...thread.querySelectorAll('[data-message-id]')].some((node) => node.dataset.messageId === message.id)) return;
    const article = element('article', `message message-${message.role === 'user' ? 'user' : 'assistant'}`);
    article.dataset.messageId = message.id;
    const meta = element('div', 'message-meta');
    if (message.role === 'assistant') {
      meta.append(element('span', 'avatar assistant-avatar', '✳'));
      meta.append(element('strong', '', 'femaktiv'));
      meta.append(element('span', 'example-label', form.dataset.placeholder));
    } else meta.append(element('strong', '', form.dataset.you));
    article.append(meta, element('div', 'message-content', message.content));
    if (message.context?.length) {
      const details = element('details', 'message-context');
      details.append(element('summary', '', `${form.dataset.context} (${message.context.length})`));
      message.context.forEach((note) => {
        const snapshot = element('div', 'snapshot');
        snapshot.append(element('strong', '', note.title), element('p', '', note.body));
        details.append(snapshot);
      });
      article.append(details);
    }
    thread.append(article);
  };
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (pending || !input.value.trim() || !present()) return;
    const content = input.value.trim();
    const noteIds = noteInputs.filter((note) => note.checked).map((note) => note.value);
    if (noteIds.length > 5) { status.textContent = form.dataset.noteLimit; return; }
    const fingerprint = JSON.stringify({ content, note_ids: noteIds });
    if (!lastAttempt || lastAttempt.fingerprint !== fingerprint) {
      lastAttempt = { fingerprint, id: crypto.randomUUID() };
    }
    pending = true;
    sendButton.disabled = true;
    input.readOnly = true;
    form.setAttribute('aria-busy', 'true');
    updateNotes();
    status.classList.remove('is-error');
    status.textContent = form.dataset.sending;
    controller = new AbortController();
    try {
      const response = await fetch(form.action, {
        method: 'POST', credentials: 'same-origin', signal: controller.signal,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value },
        body: JSON.stringify({ content, note_ids: noteIds, client_request_id: lastAttempt.id }),
      });
      const result = await response.json();
      if (!present()) return;
      if (!response.ok) throw new Error(result.error?.message || form.dataset.error);
      if (result.chat.id !== chatId || result.mode !== 'placeholder') throw new Error(form.dataset.error);
      thread.querySelector('[data-thread-empty]')?.remove();
      appendMessage(result.user_message);
      appendMessage(result.assistant_message);
      document.querySelector('[data-chat-title]').textContent = result.chat.title;
      const historyTitle = document.querySelector(`[data-chat-link="${chatId}"] span`);
      if (historyTitle) historyTitle.textContent = result.chat.title;
      const renameInput = document.querySelector('#rename-title');
      if (renameInput) renameInput.value = result.chat.title;
      document.title = `${result.chat.title} · femaktiv`;
      input.value = '';
      input.style.height = '';
      form.querySelector('[data-char-count]').textContent = '0';
      noteInputs.forEach((note) => { note.checked = false; });
      form.querySelector('.note-picker').open = false;
      lastAttempt = null;
      status.textContent = form.dataset.saved;
      thread.scrollTop = thread.scrollHeight;
    } catch (error) {
      if (present() && error.name !== 'AbortError') {
        status.classList.add('is-error');
        status.textContent = error instanceof TypeError || error instanceof SyntaxError ? form.dataset.error : error.message;
      }
    } finally {
      pending = false;
      if (present()) {
        sendButton.disabled = false;
        input.readOnly = false;
        form.removeAttribute('aria-busy');
        updateNotes();
        input.focus();
      }
    }
  });
  thread.scrollTop = thread.scrollHeight;
})();
