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
  let contextBusy = false;
  let contextEpoch = 0;
  let contextController = null;
  let contextUncertain = false;
  const contextPanel = document.querySelector('[data-live-context]');
  let activeContext = JSON.parse(document.querySelector('#active-context-data')?.textContent || 'null');
  const present = () => !navigating && form.isConnected && window.location.pathname === initialPath;
  const prepareNavigation = () => { navigating = true; controller?.abort(); contextController?.abort(); };
  window.addEventListener('pagehide', prepareNavigation);
  window.addEventListener('pageshow', (event) => { if (event.persisted) window.location.reload(); });
  document.addEventListener('submit', (event) => {
    if (event.target !== form && !event.defaultPrevented) prepareNavigation();
  });
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || link.target === '_blank' || link.hasAttribute('download')) return;
    const destination = new URL(link.href, window.location.href);
    if (!['https:', 'http:'].includes(destination.protocol)) return;
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
  const sourceLink = (url, label) => {
    const link = element('a', '', label);
    try {
      const target = new URL(url);
      if (!['https:', 'http:'].includes(target.protocol) || target.username || target.password) return element('span', '', label);
      link.href = target.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    } catch { return element('span', '', label); }
    return link;
  };
  const renderContext = (value) => {
    if (!contextPanel || !value) return;
    activeContext = value;
    contextPanel.querySelector('[data-active-count]').textContent = String(value.notes.length);
    const list = contextPanel.querySelector('[data-active-notes]');
    list.replaceChildren();
    if (!value.notes.length) list.append(element('p', '', contextPanel.dataset.empty));
    value.notes.forEach((note) => {
      const item = element('div', 'active-note');
      const preview = element('details', '');
      preview.append(element('summary', '', note.title), element('p', '', note.body));
      const actions = element('div', 'active-note-actions');
      ['remove', 'refresh'].forEach((action) => {
        const button = element('button', 'button button-small button-secondary', contextPanel.dataset[action]);
        button.type = 'button';
        button.disabled = action === 'refresh' && !note.can_refresh;
        button.addEventListener('click', () => changeContext({ action, note_id: note.id }));
        actions.append(button);
      });
      item.append(preview, actions);
      list.append(item);
    });
  };
  const changeContext = async (payload) => {
    if (contextBusy || !present()) return;
    contextBusy = true;
    contextPanel.setAttribute('aria-busy', 'true');
    contextController = new AbortController();
    const requestController = contextController;
    const contextTimeout = setTimeout(() => requestController.abort(new DOMException(contextPanel.dataset.failed, 'TimeoutError')), 15000);
    status.classList.remove('is-error');
    try {
      const response = await fetch(contextPanel.dataset.url, {
        method: 'POST', credentials: 'same-origin', signal: contextController.signal,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!present()) return;
      if (!response.ok) throw new Error(result.error?.message || form.dataset.error);
      contextEpoch += 1;
      controller?.abort();
      lastAttempt = null;
      renderContext(result.active_context);
      if (payload.action === 'remove') {
        noteInputs.forEach((note) => { if (note.value === payload.note_id) note.checked = false; });
        updateNotes();
      }
      status.textContent = contextPanel.dataset.updated;
    } catch (error) {
      if (present() && error.name !== 'AbortError') {
        status.classList.add('is-error');
        contextUncertain = error instanceof TypeError || error instanceof SyntaxError || error.name === 'TimeoutError';
        status.textContent = contextUncertain ? contextPanel.dataset.failed : error.message;
      }
    } finally {
      clearTimeout(contextTimeout);
      contextBusy = false;
      contextPanel.removeAttribute('aria-busy');
    }
  };
  contextPanel?.querySelector('[data-context-reset]').addEventListener('click', () => changeContext({ action: 'reset' }));
  renderContext(activeContext);
  const appendMessage = (message) => {
    if ([...thread.querySelectorAll('[data-message-id]')].some((node) => node.dataset.messageId === message.id)) return;
    const article = element('article', `message message-${message.role === 'user' ? 'user' : 'assistant'}`);
    article.dataset.messageId = message.id;
    const meta = element('div', 'message-meta');
    if (message.role === 'assistant') {
      const avatar = element('img', 'brand-logo avatar assistant-avatar');
      avatar.src = form.dataset.logoUrl;
      avatar.alt = '';
      avatar.width = 2048;
      avatar.height = 2048;
      meta.append(avatar);
      meta.append(element('strong', '', 'femaktiv'));
      meta.append(element('span', 'example-label', message.mode === 'live' ? form.dataset.liveLabel : form.dataset.placeholder));
    } else meta.append(element('strong', '', form.dataset.you));
    article.append(meta);
    if (message.paragraphs?.length) {
      const body = element('div', 'message-content cited-reply');
      message.paragraphs.forEach((paragraph) => {
        const block = element('div', 'answer-paragraph');
        block.append(element('p', '', paragraph.text));
        if (paragraph.citations?.length) {
          const links = element('div', 'paragraph-citations');
          paragraph.citations.forEach((source) => links.append(sourceLink(source.url, source.title)));
          block.append(links);
        }
        body.append(block);
      });
      if (message.urgent_help?.contacts?.length) {
        const help = element('section', 'urgent-help');
        const heading = element('h3', '', message.urgent_help.heading);
        heading.id = `urgent-help-${message.id}`;
        help.setAttribute('aria-labelledby', heading.id);
        const contacts = element('ul', 'urgent-help-contacts');
        message.urgent_help.contacts.forEach((contact) => {
          const item = element('li', '');
          const title = element('div', 'urgent-help-contact-title');
          const phone = element('a', 'urgent-help-number', contact.number);
          phone.href = `tel:${contact.number}`;
          title.append(phone, element('strong', '', contact.label));
          const source = sourceLink(contact.source_url, contact.source_title);
          source.classList.add('urgent-help-source');
          item.append(title, element('p', '', contact.description), source);
          contacts.append(item);
        });
        help.append(heading, contacts);
        body.append(help);
      }
      (message.citations || []).forEach((source) => {
        const card = element('details', 'source-card');
        card.open = source.kind === 'contact';
        card.append(element('summary', '', source.title), sourceLink(source.url, form.dataset.openSource));
        if (source.kind === 'contact') {
          card.append(element('p', '', source.locality));
          [...(source.phones || []), ...(source.emails || [])].forEach((contact) => card.append(element('p', '', contact)));
          card.append(element('p', '', form.dataset.contactUnknown));
        } else card.append(element('p', '', source.section));
        card.append(element('p', 'source-checked', `${form.dataset.checked}: ${source.checked_date}`));
        if (source.updated_date || source.publication_date) card.append(element('p', 'source-checked', `${form.dataset.sourceDate}: ${source.updated_date || source.publication_date}`));
        body.append(card);
      });
      article.append(body);
    } else article.append(element('div', 'message-content', message.content));
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
    if (pending || contextBusy || !input.value.trim() || !present()) return;
    if (contextUncertain) { status.textContent = contextPanel.dataset.failed; return; }
    const submittedEpoch = contextEpoch;
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
    const requestController = controller;
    const requestTimeout = setTimeout(() => requestController.abort(new DOMException(form.dataset.error, 'TimeoutError')), 75000);
    try {
      let response = await fetch(form.action, {
        method: 'POST', credentials: 'same-origin', signal: controller.signal,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value },
        body: JSON.stringify({ content, note_ids: noteIds, client_request_id: lastAttempt.id }),
      });
      let result = await response.json();
      const pollingDeadline = Date.now() + 65000;
      while (response.status === 202 && result.status === 'processing') {
        if (!present() || contextBusy || contextEpoch !== submittedEpoch) return;
        if (Date.now() > pollingDeadline) throw new Error(form.dataset.error);
        await new Promise((resolve) => setTimeout(resolve, 1000));
        response = await fetch(form.dataset.turnUrl.replace('00000000-0000-0000-0000-000000000000', lastAttempt.id), {
          credentials: 'same-origin', signal: controller.signal, cache: 'no-store',
        });
        result = await response.json();
      }
      if (!present() || contextBusy || contextEpoch !== submittedEpoch) return;
      if (!response.ok) {
        renderContext(result.active_context);
        if (result.error?.terminal) lastAttempt = null; // Only a deliberate new send can incur another call.
        throw new Error(result.error?.message || form.dataset.error);
      }
      if (result.chat?.id !== chatId || !['placeholder', 'live'].includes(result.mode)) throw new Error(form.dataset.error);
      thread.querySelector('[data-thread-empty]')?.remove();
      appendMessage(result.user_message);
      appendMessage(result.assistant_message);
      renderContext(result.active_context);
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
      clearTimeout(requestTimeout);
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
