const modal = document.querySelector('[data-modal]');
const openButton = document.querySelector('[data-open-modal]');
const closeButton = document.querySelector('[data-close-modal]');
if (modal && openButton) {
  const close = () => modal.setAttribute('aria-hidden', 'true');
  openButton.addEventListener('click', () => { modal.setAttribute('aria-hidden', 'false'); modal.querySelector('input[name="title"]').focus(); });
  closeButton.addEventListener('click', close);
  modal.addEventListener('click', (event) => { if (event.target === modal) close(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') close(); });
}
const mobileMenu = document.querySelector('.mobile-menu');
const sidebar = document.querySelector('.sidebar');
if (mobileMenu && sidebar) mobileMenu.addEventListener('click', () => sidebar.classList.toggle('open'));