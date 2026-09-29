import { readJSON } from '../shared/http.js';
import { content } from './content.js';
import { appearance } from './appearance.js';
import { settings } from './settings.js';
import { images } from './images.js';
import { services } from './services.js';
import { history } from './history.js';
export let data,
    defaults,
    labels,
    revision,
    csrf,
    dirty = false,
    tab = 'Contenido',
    busy = false,
    ready = false;

export const editor = document.getElementById('editor');

export const clone = (x) => structuredClone(x);

export const names = {
    background: 'Fondo principal',
    primary: 'Color principal',
    foreground: 'Texto',
    gold: 'Acento',
    secondary: 'Color secundario',
    muted: 'Texto secundario',
    border: 'Bordes',
    font: 'Tipografía de texto',
    heading: 'Tipografía de títulos',
    whatsapp: 'WhatsApp de cotizaciones (código de país + número)',
    contactWhatsapp: 'WhatsApp de contacto',
    instagram: 'Instagram',
    facebook: 'Facebook',
    tiktok: 'TikTok',
    base: 'Precio base novia',
    companion: 'Precio por acompañante',
    hair: 'Peinado por persona',
    trial: 'Prueba de maquillaje',
    name: 'Nombre',
    slug: 'Identificador único',
    short: 'Descripción corta',
    description: 'Descripción completa',
    price: 'Nota de precio',
    price_amount: 'Precio de referencia (MXN)',
    duration: 'Duración',
    includes: 'Elementos incluidos (uno por línea)'
};

export function el(tag, text, cls) {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
}

export function message(s) {
    document.getElementById('message').textContent = s;
}

export function changed() {
    dirty = true;
    document.getElementById('state').textContent = 'Cambios sin guardar';
}

export async function api(path, body) {
    const r = await fetch('/api/' + path, {
        method: body === undefined ? 'GET' : 'POST',
        headers:
            body === undefined
                ? { Accept: 'application/json' }
                : {
                      'Content-Type': 'application/json',
                      'X-CSRF-Token': csrf
                  },
        body: body === undefined ? undefined : JSON.stringify(body)
    });
    const result = await readJSON(r);
    if (!r.ok) {
        if (r.status === 401)
            message(
                'Tu sesión venció. Abre /login en otra pestaña, inicia sesión y recarga este panel. Los cambios sin guardar no se recuperan al recargar.'
            );
        throw Error(result.error || 'No se pudo completar la operación.');
    }
    return result;
}

export function button(text, handler, cls) {
    const b = el('button', text, cls);
    b.type = 'button';
    b.onclick = () => run(handler);
    return b;
}

export async function run(fn) {
    try {
        await fn();
    } catch (e) {
        if (!ready) document.getElementById('state').textContent = 'No se pudo cargar el panel';
        message(e.message);
    }
}

export function field(parent, label, value, set, type = 'text', options) {
    const wrap = el('label', label);
    let input;
    if (type === 'select') {
        input = el('select');
        options.forEach((v) => {
            const o = el('option', Array.isArray(v) ? v[1] : v);
            o.value = Array.isArray(v) ? v[0] : v;
            input.append(o);
        });
    } else input = el(type === 'textarea' ? 'textarea' : 'input');
    if (input.tagName === 'INPUT') input.type = type;
    input.value = value;
    input.maxLength =
        label === 'Título SEO'
            ? 150
            : label === 'Descripción SEO'
              ? 300
              : label === 'Texto alternativo'
                ? 250
                : ['Instagram', 'Facebook', 'TikTok'].includes(label)
                  ? 300
                  : label === 'Identificador único'
                    ? 60
                    : 5000;
    if (label === names.includes) input.maxLength = 15049;
    if (type === 'number') {
        input.min = 0;
        input.max = 1000000;
        input.step = '0.01';
    }
    input.addEventListener(type === 'select' ? 'change' : 'input', () => {
        if (label === names.includes) {
            const items = input.value.split('\n').filter((line) => line.trim());
            input.setCustomValidity(
                items.length > 50 || items.some((line) => line.length > 300)
                    ? 'Máximo 50 elementos de hasta 300 caracteres cada uno.'
                    : ''
            );
        }
        set(type === 'number' ? Number(input.value) : input.value);
        changed();
    });
    wrap.append(input);
    parent.append(wrap);
    return input;
}

export function card(title, parent = editor) {
    const n = el('section', undefined, 'card');
    if (title) n.append(el('h3', title));
    parent.append(n);
    return n;
}

export async function load() {
    const result = await api('admin/content');
    data = result.content;
    defaults = result.defaults;
    labels = result.labels;
    revision = result.revision;
    dirty = false;
    document.getElementById('state').textContent = 'Borrador guardado · versión ' + revision;
    render();
}

export function render() {
    for (const url of previewURLs) URL.revokeObjectURL(url);
    previewURLs.clear();
    editor.replaceChildren();
    document.querySelectorAll('#nav button').forEach((b) => {
        b.classList.toggle('active', b.textContent === tab);
        b.setAttribute('aria-current', b.textContent === tab ? 'page' : 'false');
    });
    editor.append(el('h2', tab), el('p', sectionDescriptions[tab], 'section-intro'));
    ({
        Contenido: content,
        Imágenes: images,
        Apariencia: appearance,
        Servicios: services,
        Configuración: settings,
        Historial: history
    })[tab]();
}

export const sectionDescriptions = {
    Contenido: 'Elige una sección de la página para editar sus textos y botones.',
    Servicios: 'Organiza tu catálogo. Abre un servicio para editar sus detalles y fotografías.',
    Imágenes: 'Administra las fotografías del sitio y tu biblioteca de imágenes.',
    Apariencia: 'Personaliza la paleta de colores y las tipografías de tu sitio.',
    Configuración:
        'Encuentra los datos de contacto, las redes sociales y los precios en grupos separados.',
    Historial: 'Consulta las versiones guardadas y recupera un borrador anterior.'
};

export const openPanels = new Set();

export function panel(title, key, parent = editor, initial = false) {
    const details = el('details', undefined, 'card editor-group');
    details.open = openPanels.has(key) || initial;
    const summary = el('summary', title);
    const body = el('div', undefined, 'group-body');
    details.append(summary, body);
    details.addEventListener('toggle', () => {
        if (details.open) openPanels.add(key);
        else openPanels.delete(key);
    });
    parent.append(details);
    return body;
}

export async function save() {
    for (const control of editor.querySelectorAll('input, textarea, select')) {
        if (!control.checkValidity()) {
            control.closest('details')?.setAttribute('open', '');
            control.reportValidity();
            throw Error('Revisa los campos señalados antes de guardar.');
        }
    }
    const result = await api('admin/draft', {
        revision,
        content: data
    });
    revision = result.revision;
    dirty = false;
    document.getElementById('state').textContent = 'Borrador guardado · versión ' + revision;
    message('Borrador guardado. La web pública no ha cambiado.');
}

export async function exclusive(fn) {
    if (busy || !ready) return;
    busy = true;
    editor.inert = true;
    document.getElementById('nav').inert = true;
    const controls = ['save', 'publish', 'preview', 'logout', 'revoke'];
    controls.forEach((id) => (document.getElementById(id).disabled = true));
    try {
        await fn();
    } finally {
        busy = false;
        editor.inert = false;
        document.getElementById('nav').inert = false;
        controls.forEach((id) => (document.getElementById(id).disabled = false));
    }
}

export async function logout(all) {
    if (dirty && !(await ask('Hay cambios sin guardar. ¿Salir y descartarlos?'))) return;
    if (all && !(await ask('¿Cerrar todas las sesiones del administrador, incluida esta?'))) return;
    await api('admin/' + (all ? 'revoke' : 'logout'), {});
    dirty = false;
    location.assign('/login');
}

export function ask(text) {
    return new Promise((resolve) => {
        const d = el('dialog');
        d.className = 'confirmation';
        d.setAttribute('aria-label', 'Confirmar acción');
        d.append(el('h2', 'Confirmar acción'), el('p', text));
        const actions = el('div', undefined, 'actions');
        actions.append(
            button('Cancelar', () => d.close('cancel')),
            button('Confirmar', () => d.close('yes'), 'primary')
        );
        d.append(actions);
        d.addEventListener(
            'close',
            () => {
                const answer = d.returnValue === 'yes';
                d.remove();
                resolve(answer);
            },
            {
                once: true
            }
        );
        document.body.append(d);
        d.showModal();
    });
}
export const previewURLs = new Set();
const serviceKeys = new WeakMap();
let serviceSequence = 0;
export function serviceKey(service) {
    if (!serviceKeys.has(service)) serviceKeys.set(service, 'service-' + ++serviceSequence);
    return serviceKeys.get(service);
}

export function init() {
    document.getElementById('save').onclick = () => run(() => exclusive(save));
    document.getElementById('publish').onclick = () =>
        run(() =>
            exclusive(async () => {
                if (!(await ask('¿Publicar el contenido de este borrador en la web pública?')))
                    return;
                if (dirty) await save();
                const result = await api('admin/publish', {
                    revision
                });
                revision = result.revision;
                document.getElementById('state').textContent = 'Publicado · versión ' + revision;
                message('Contenido publicado correctamente.');
            })
        );
    document.getElementById('preview').onclick = () =>
        run(() =>
            exclusive(async () => {
                if (dirty) await save();
                document.getElementById('preview-frame').src = '/preview?v=' + revision;
                document.getElementById('preview-dialog').showModal();
            })
        );
    document.getElementById('preview-close').onclick = () =>
        document.getElementById('preview-dialog').close();
    document.getElementById('desktop').onclick = () =>
        (document.getElementById('preview-frame').style.width = '1280px');
    document.getElementById('mobile').onclick = () =>
        (document.getElementById('preview-frame').style.width = '390px');
    document.getElementById('logout').onclick = () => run(() => logout(false));
    document.getElementById('revoke').onclick = () => run(() => logout(true));
    window.addEventListener('beforeunload', (e) => {
        if (dirty || busy) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
    for (const title of [
        'Contenido',
        'Servicios',
        'Imágenes',
        'Apariencia',
        'Configuración',
        'Historial'
    ])
        document.getElementById('nav').append(
            button(title, () => {
                tab = title;
                render();
                editor.focus({ preventScroll: true });
            })
        );
    editor.inert = true;
    document.getElementById('nav').inert = true;
    ['save', 'publish', 'preview'].forEach((id) => (document.getElementById(id).disabled = true));
    run(async () => {
        const s = await api('session');
        csrf = s.csrf;
        await load();
        ready = true;
        editor.inert = false;
        document.getElementById('nav').inert = false;
        ['save', 'publish', 'preview'].forEach(
            (id) => (document.getElementById(id).disabled = false)
        );
    });
}
