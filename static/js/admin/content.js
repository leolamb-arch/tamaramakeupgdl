import { data, labels, editor, el, field, card, panel } from './editor.js';
const textSections = [
    ['Navegación y menú', 0, 7],
    ['Portada e introducción', 8, 15],
    ['Presentación de servicios', 16, 18],
    ['Encuentra tu look', 19, 27],
    ['Cotización: introducción', 28, 35],
    ['Cotización: datos del evento', 36, 46],
    ['Cotización: fecha, horario y envío', 47, 63],
    ['Calculadora de grupos y novias', 64, 78],
    ['Contacto', 79, 85],
    ['Testimonios', 86, 95],
    ['Pie de página', 96, 103],
    ['Mensajes flotantes', 104, 107],
    ['Menú móvil', 108, 114],
    ['Visor de fotografías', 115, 120]
];

export function content() {
    const tools = card('Encuentra lo que quieres editar');
    const search = el('input');
    search.type = 'search';
    search.placeholder = 'Buscar un texto o botón en todas las secciones…';
    search.setAttribute('aria-label', 'Buscar textos');
    tools.append(search);
    const count = el('p', '', 'muted search-count');
    count.setAttribute('role', 'status');
    tools.append(count);
    const list = el('div');
    editor.append(list);
    function draw() {
        list.replaceChildren();
        const query = search.value.trim().toLocaleLowerCase('es');
        const matches = Object.entries(data.texts).filter(([k, v]) =>
            ((labels[k] || '') + ' ' + v).toLocaleLowerCase('es').includes(query)
        );
        count.textContent =
            matches.length + ' textos' + (query ? ' encontrados' : ' organizados por sección');
        const groups = [...textSections, ['Otros textos', 121, Infinity]];
        groups.forEach(([title, min, max]) => {
            const rows = matches.filter(([k]) => {
                const n = Number(k.slice(1));
                return n >= min && n <= max;
            });
            if (!rows.length) return;
            const body = panel(title + ' · ' + rows.length, 'texts-' + min, list, Boolean(query));
            body.classList.add('text-fields');
            rows.forEach(([k, v]) =>
                field(
                    body,
                    labels[k] || k,
                    v,
                    (x) => (data.texts[k] = x),
                    v.length > 85 ? 'textarea' : 'text'
                )
            );
        });
        if (!matches.length)
            list.append(el('p', 'No hay coincidencias. Prueba con otra palabra.', 'card'));
    }
    search.oninput = draw;
    draw();
    const seo = panel('Buscadores · título y descripción SEO', 'seo');
    field(seo, 'Título SEO', data.seo.title, (v) => (data.seo.title = v));
    field(
        seo,
        'Descripción SEO',
        data.seo.description,
        (v) => (data.seo.description = v),
        'textarea'
    );
}
