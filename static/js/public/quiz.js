import { $, escapeHTML } from './shared.js';
import { CMS, SERVICES } from './content.js';
import { info } from './navigation.js';
// Quiz local: correspondencia reconstruida a partir de las opciones públicas.
let eventChoice = '',
    extraChoice = '';
[
    ['events', ['Boda', 'Fiesta de Noche', 'Evento de Día', 'Sesión de Fotos']],
    ['extras', ['Solo maquillaje', 'Maquillaje y Peinado', 'Solo Peinado', 'Paquete Grupal']]
].forEach(([id, options]) => {
    $('#' + id).innerHTML = options
        .map((x) => `<button class="choice" type="button" aria-pressed="false">${x}</button>`)
        .join('');
    $('#' + id)
        .querySelectorAll('button')
        .forEach(
            (b) =>
                (b.onclick = () => {
                    if (id === 'events') eventChoice = b.textContent;
                    else extraChoice = b.textContent;
                    $('#' + id)
                        .querySelectorAll('button')
                        .forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
                    $('#recommend').disabled = !(eventChoice && extraChoice);
                    $('#quiz-result').innerHTML = '';
                    $('#quiz-help').textContent =
                        eventChoice && extraChoice
                            ? '¡Todo listo para encontrar tu look!'
                            : CMS.texts.t027;
                })
        );
});
$('#recommend').onclick = () => {
    const slug = {
            Boda: 'novia',
            'Fiesta de Noche': 'eventos',
            'Evento de Día': 'social',
            'Sesión de Fotos': 'editorial'
        }[eventChoice],
        s = SERVICES.find((x) => (x.quiz_slug || x.slug) === slug);
    if (!s) {
        info(
            'Servicios',
            'Este servicio no está publicado por ahora. Consulta el catálogo o contáctanos.'
        );
        return;
    }
    $('#quiz-result').innerHTML =
        `<div class="result"><h3>${escapeHTML(extraChoice === 'Solo Peinado' ? 'Servicio de peinado' : s.name)}</h3><p>${escapeHTML(extraChoice === 'Solo Peinado' ? 'Consulta las opciones de peinado para tu evento.' : s.short)}</p><p class="small">${escapeHTML(extraChoice)}</p><a class="pill primary" href="${extraChoice === 'Paquete Grupal' ? '#cotizacion-grupos' : '#cotizar'}">Pedir cotización</a><button class="pill" id="quiz-reset">Volver a empezar</button></div>`;
    $('#servicio').value = s.slug;
    $('#quiz-reset').onclick = () => {
        eventChoice = extraChoice = '';
        document
            .querySelectorAll('.quiz .choice')
            .forEach((b) => b.setAttribute('aria-pressed', 'false'));
        $('#recommend').disabled = true;
        $('#quiz-result').innerHTML = '';
        $('#quiz-help').textContent = CMS.texts.t027;
    };
};
