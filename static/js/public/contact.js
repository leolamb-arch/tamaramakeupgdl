import { $, money, state } from './shared.js';
import { CMS } from './content.js';
import { info } from './navigation.js';
import { groupTotal } from './calculator.js';
document.querySelectorAll('[data-social]').forEach((b) => {
    const url = CMS.settings[b.dataset.social.toLowerCase()];
    b.onclick = () => {
        if (url) window.open(url, '_blank', 'noopener,noreferrer');
        else
            info(
                `${b.dataset.social}: enlace pendiente`,
                'El sitio original contiene una dirección de ejemplo para esta red. Configura tu perfil real antes de habilitar este enlace.'
            );
    };
});
document.querySelectorAll('a[href^="https://wa.me/"]').forEach((a) => {
    if (CMS.settings.contactWhatsapp) a.href = 'https://wa.me/' + CMS.settings.contactWhatsapp;
    else {
        a.removeAttribute('href');
        a.setAttribute('role', 'button');
        a.tabIndex = 0;
        a.onclick = () => info('Contacto', 'WhatsApp pendiente de configurar.');
        a.onkeydown = (e) => {
            if (['Enter', ' '].includes(e.key)) {
                e.preventDefault();
                a.click();
            }
        };
    }
});
if (CMS.settings.whatsapp) {
    document.getElementById('floating-whatsapp').onclick = () =>
        window.open('https://wa.me/' + CMS.settings.whatsapp, '_blank', 'noopener,noreferrer');
    document.getElementById('group-whatsapp').onclick = () =>
        window.open(
            'https://wa.me/' +
                CMS.settings.whatsapp +
                '?text=' +
                encodeURIComponent(
                    'Hola, quisiera consultar esta cotización estimada: ' +
                        money(groupTotal()) +
                        '. Acompañantes: ' +
                        state.count +
                        '. Peinado: ' +
                        (document.getElementById('hair').checked ? 'Sí' : 'No') +
                        '. Prueba: ' +
                        (document.getElementById('trial').checked ? 'Sí' : 'No') +
                        '. Sujeta a disponibilidad; sin reserva confirmada.'
                ),
            '_blank',
            'noopener,noreferrer'
        );
} else {
    $('#floating-whatsapp').onclick = () =>
        info(
            'WhatsApp pendiente de configurar',
            'El botón flotante original usa un número de ejemplo. El enlace de WhatsApp de la sección Contacto conserva el número público observado. Confirma el destino antes de conectar este botón.'
        );
    $('#group-whatsapp').onclick = () =>
        info(
            'Cotización preparada',
            `Total estimado: ${money(groupTotal())}. El WhatsApp de cotización del original contiene un número de ejemplo. Configura el destino para habilitar el envío. No se ha enviado ningún mensaje.`
        );
}
if (CMS.texts.t074 === CMS.dynamic_defaults.t074)
    document.querySelector('label:has(#hair) span:last-child').textContent =
        '+' + money(CMS.settings.hair) + ' por persona';
if (CMS.texts.t076 === CMS.dynamic_defaults.t076)
    document.querySelector('label:has(#trial) span:last-child').textContent =
        '+' + money(CMS.settings.trial);

function refreshImage(img) {
    const m = CMS.images[img.dataset.image];
    if (!m) return;
    img.alt = m.alt;
    img.style.objectPosition = m.x + '% ' + m.y + '%';
}
document.querySelectorAll('img[data-image]').forEach(refreshImage);
new MutationObserver((records) => {
    for (const record of records) {
        if (record.type === 'attributes') refreshImage(record.target);
        else
            for (const node of record.addedNodes) {
                if (node.nodeType !== 1) continue;
                if (node.matches('img[data-image]')) refreshImage(node);
                node.querySelectorAll('img[data-image]').forEach(refreshImage);
            }
    }
}).observe(document.body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['data-image', 'src']
});

if (CMS.texts.t068 === CMS.dynamic_defaults.t068)
    document.querySelector('.group-panel .small').textContent =
        money(CMS.settings.companion) + ' por persona adicional.';
