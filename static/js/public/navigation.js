import { $, escapeHTML, modal } from './shared.js';
import { CMS } from './content.js';
export function openModal(html, kind = '') {
    modal.className = kind;
    $('#modal-body').innerHTML = html;
    if (!modal.open) modal.showModal();
}

export function info(title, text) {
    openModal(`<h2 id="modal-title">${escapeHTML(title)}</h2><p>${escapeHTML(text)}</p>`);
}
document
    .querySelectorAll('[data-close]')
    .forEach((b) => b.addEventListener('click', () => b.closest('dialog').close()));
document.querySelectorAll('dialog').forEach((d) =>
    d.addEventListener('click', (e) => {
        if (e.target === d) {
            const r = d.getBoundingClientRect();
            if (
                e.clientX < r.left ||
                e.clientX > r.right ||
                e.clientY < r.top ||
                e.clientY > r.bottom
            )
                d.close();
        }
    })
);
$('#menu-open').onclick = () => {
    $('#mobile-menu').showModal();
    $('#menu-open').setAttribute('aria-expanded', 'true');
};
$('#mobile-menu').addEventListener('close', () => {
    $('#menu-open').setAttribute('aria-expanded', 'false');
});
$('#mobile-menu')
    .querySelectorAll('a')
    .forEach((link) => {
        link.onclick = () => $('#mobile-menu').close();
    });

document.querySelectorAll('[data-admin]').forEach((button) => {
    button.onclick = () => {
        const mobileMenu = $('#mobile-menu');

        if (mobileMenu?.open) {
            mobileMenu.close();
        }

        location.assign('/admin');
    };
});
$('#chat-close').onclick = () => ($('#chat-message').hidden = true);
if (CMS.texts.t102 === CMS.dynamic_defaults.t102) $('#year').textContent = new Date().getFullYear();
