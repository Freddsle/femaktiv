(() => {
  'use strict';
  const toggle = document.querySelector('.mobile-menu');
  const nav = document.querySelector('#main-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }
  document.querySelectorAll('.form-field.has-error input, .form-field.has-error textarea').forEach((field) => {
    field.setAttribute('aria-invalid', 'true');
    const error = document.getElementById(`${field.id}_error`);
    if (error) field.setAttribute('aria-describedby', `${field.getAttribute('aria-describedby') || ''} ${error.id}`.trim());
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('.account-menu[open], .chat-options[open], .note-picker[open]').forEach((details) => {
      details.open = false;
      details.querySelector('summary').focus();
    });
  });
})();
