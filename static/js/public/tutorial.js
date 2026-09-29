import { $, modal } from './shared.js';

import { openModal } from './navigation.js';
const tutorial = [
    [
        '¡Bienvenida! 💕',
        'Soy Tamara y me alegra mucho que estés aquí. En menos de un minuto te mostraré cómo moverte por el sitio y cómo llegar a reservar tu maquillaje. ¿Lista?',
        null
    ],
    [
        'Explora mis servicios',
        'Aquí están todos los tipos de maquillaje que ofrezco: social, novia, XV años, editorial, graduaciones y más. Toca cada tarjeta para ver fotos y detalles.',
        '#servicios'
    ],
    [
        'Pide tu cotización',
        'Elige el servicio, la fecha y la hora. Revisa el resumen y envía tu solicitud; Tamara deberá confirmar la cita.',
        '#cotizar'
    ],
    [
        'Contacto y contratación',
        'Aquí encuentras las redes y datos de contacto. La confirmación y las condiciones del anticipo se acuerdan directamente con Tamara.',
        '#contacto'
    ],
    [
        '¿Dudas? Escríbeme por WhatsApp',
        'El botón flotante permite acceder al contacto una vez configurado con el número correcto.',
        '#floating-whatsapp'
    ]
];
let tutorialStep = 0;

function renderTutorial() {
    const [title, body, target] = tutorial[tutorialStep];
    if (target)
        $(target).scrollIntoView({
            block: 'center',
            behavior: 'smooth'
        });
    openModal(
        `<p class="eyebrow">Paso ${tutorialStep + 1} de 5</p><h2 id="modal-title">${title}</h2><p>${body}</p><div class="tutorial-actions"><button class="pill" id="tutorial-skip">Omitir</button>${tutorialStep ? '<button class="pill" id="tutorial-prev">Anterior</button>' : ''}<button class="pill primary" id="tutorial-next">${tutorialStep === 4 ? 'Finalizar' : 'Siguiente'}</button></div>`,
        'tutorial-dialog'
    );
    $('#tutorial-skip').onclick = () => modal.close();
    if ($('#tutorial-prev'))
        $('#tutorial-prev').onclick = () => {
            tutorialStep--;
            renderTutorial();
        };
    $('#tutorial-next').onclick = () => {
        if (tutorialStep === 4) modal.close();
        else {
            tutorialStep++;
            renderTutorial();
        }
    };
}
document.querySelectorAll('[data-tutorial]').forEach(
    (b) =>
        (b.onclick = () => {
            $('#mobile-menu').close();
            tutorialStep = 0;
            renderTutorial();
        })
);
