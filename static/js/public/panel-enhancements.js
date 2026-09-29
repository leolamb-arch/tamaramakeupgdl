/** New editor fields activate only after the owner saves them. Existing public
 * content, layout, images and demo-only booking behavior remain the baseline. */
import { CMS, SERVICES } from './content.js';
import { $, state, escapeHTML as esc } from './shared.js';
import { setConfiguredTotal } from './calculator.js';
const config = CMS.panel || {};
const node = (tag, text, cls) => {
    const element = document.createElement(tag);
    if (text != null) element.textContent = text;
    if (cls) element.className = cls;
    return element;
};
function button(text, fn) {
    const b = node('button', text, 'pill'); b.type = 'button'; b.onclick = fn; return b;
}
if (config.testimonials) {
    const parent = $('.testimonials'); parent.replaceChildren();
    for (const item of config.testimonials) {
        const figure = node('figure'), stars = node('div', '★'.repeat(item.rating), 'stars');
        stars.setAttribute('aria-label', `${item.rating} de 5 estrellas`);
        const caption = node('figcaption'), details = node('div', item.name);
        details.append(node('p', item.event));
        if (item.photo) { const img = node('img'); img.src = item.photo; img.alt = item.name; img.loading = 'lazy'; caption.append(img); }
        caption.append(details); figure.append(stars, caption); parent.append(figure);
    }
}
if (config.appearance?.colors?.button) {
    const style = node('style');
    style.textContent = `.pill.primary{background:hsl(${config.appearance.colors.button})}`;
    document.head.append(style);
}
if (config.email) {
    const a = node('a', config.email, 'pill'); a.href = 'mailto:' + config.email;
    $('#contacto .contact-grid > div').append(a);
}
if (config.whatsappDisplay) {
    const a = $('#contacto a[href^="https://wa.me/"]');
    if (a) a.textContent = config.whatsappDisplay;
}
if (config.calculator) {
    const c = config.calculator, text = c.texts || {}, checked = new Set();
    let format;
    try { format = new Intl.NumberFormat(c.currency.locale, { style: 'currency', currency: c.currency.code }); }
    catch { format = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }); }
    const money = n => format.format(n);
    const container = node('div');
    const old = $('#hair').closest('label'); old.before(container);
    old.remove(); $('#trial').closest('label').remove();
    const rows = () => {
        const items = [[c.baseLabel, c.basePrice]];
        if (state.count) items.push([`${c.perPersonLabel} (${state.count})`, c.perPerson * state.count]);
        for (const a of c.addons) if (checked.has(a.id)) items.push([a.label, a.price * (a.perPerson ? state.count + 1 : 1)]);
        return items;
    };
    const total = () => rows().reduce((sum, row) => sum + row[1], 0);
    setConfiguredTotal(total);
    function update() {
        $('#count').textContent = state.count;
        $('#minus').disabled = state.count === 0; $('#plus').disabled = state.count === 100;
        $('#breakdown').replaceChildren();
        for (const [label, amount] of [...rows(), [text.totalLabel || 'Total estimado', total()]]) {
            const line = node('div'); line.append(node('dt', label), node('dd', money(amount))); $('#breakdown').append(line);
        }
    }
    for (const a of c.addons) {
        const label = node('label', null, 'choice'), input = node('input'); input.type = 'checkbox';
        input.onchange = () => { input.checked ? checked.add(a.id) : checked.delete(a.id); update(); };
        label.append(input, document.createTextNode(a.label), node('span', '+' + money(a.price) + (a.perPerson ? ' por persona' : ''))); container.append(label);
    }
    $('.group-panel .small').textContent = (text.counterNote || '{price} por persona adicional.').replaceAll('{price}', money(c.perPerson));
    $('#minus').onclick = () => { state.count = Math.max(0, state.count - 1); update(); };
    $('#plus').onclick = () => { state.count = Math.min(100, state.count + 1); update(); };
    if (CMS.settings.whatsapp) $('#group-whatsapp').onclick = () => {
        const message = [text.whatsappGreeting?.replaceAll('{name}', CMS.texts.t009), ...rows().map(([label, amount]) => `${label}: ${money(amount)}`), `${text.whatsappTotalLabel}: ${money(total())}`, text.whatsappFooter].filter(Boolean).join('\n');
        window.open('https://wa.me/' + CMS.settings.whatsapp + '?text=' + encodeURIComponent(message), '_blank', 'noopener,noreferrer');
    };
    update();
}
if (config.quiz) {
    const q = config.quiz, answers = new Map(), texts = q.texts || {};
    const parent = $('.quiz'); parent.querySelectorAll('fieldset').forEach(n => n.remove());
    const fields = node('div'); parent.prepend(fields);
    function refresh() { $('#recommend').disabled = !q.questions.length || answers.size !== q.questions.length; $('#quiz-result').replaceChildren(); }
    q.questions.forEach((question, index) => {
        const field = node('fieldset'), legend = node('legend'), options = node('div', null, 'choices');
        legend.append(node('span', String(index + 1), 'step'), document.createTextNode(' ' + question.question));
        for (const option of question.options) {
            const b = button(option.label, () => {
                answers.set(question.id, option);
                options.querySelectorAll('button').forEach(other => other.setAttribute('aria-pressed', String(other === b)));
                refresh();
            });
            b.className = 'choice'; b.setAttribute('aria-pressed', 'false'); options.append(b);
        }
        field.append(legend, options); fields.append(field);
    });
    $('#recommend').onclick = () => {
        const first = answers.get(q.questions[0]?.id);
        const service = SERVICES.find(s => s.slug === first?.service || s.quiz_slug === first?.service);
        if (!service) { $('#quiz-result').textContent = 'El servicio recomendado no está disponible por ahora.'; return; }
        const result = node('div', null, 'result'); result.append(node('p', texts.resultLabel), node('h3', service.name), node('p', service.short));
        for (const answer of answers.values()) if (q.extrasNote?.[answer.id]) result.append(node('p', q.extrasNote[answer.id], 'small'));
        result.append(node('p', `${texts.priceLabel || 'Precio estimado'}: ${service.price || service.price_amount}`), node('p', `${texts.durationLabel || 'Tiempo requerido'}: ${service.duration}`));
        const link = node('a', texts.ctaButton || 'Reservar este look', 'pill primary'); link.href = '#cotizar';
        link.onclick = () => { $('#servicio').value = service.slug; };
        result.append(link, button(texts.resetButton || 'Volver a responder', () => {
            answers.clear(); fields.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed','false')); refresh();
        }));
        $('#quiz-result').replaceChildren(result);
    };
    refresh();
}
if (config.locationConfig) {
    const c = config.locationConfig, choice = $('.location-choices'), field = choice.closest('fieldset');
    field.querySelector('legend').textContent = c.sectionTitle;
    field.querySelector('p').textContent = c.sectionInstructions;
    const radios = [...choice.querySelectorAll('input')];
    radios.forEach((input, i) => {
        input.closest('label').replaceChildren(input, document.createTextNode(i ? c.externalOptionLabel : c.studioOptionLabel));
    });
    $('#address-wrap').hidden = true; $('#direccion').required = false;
    const extra = node('div'); choice.after(extra);
    const render = () => {
        extra.replaceChildren(); $('#direccion').required = false; $('#direccion').value = '';
        if (radios[0].checked) {
            extra.append(node('h4',c.studio.title),node('p',c.studio.instructions),node('p',c.studio.address));
            const copy = button(c.studio.copyLabel, async () => {
                try { await navigator.clipboard.writeText(c.studio.address); copy.textContent=c.studio.copiedLabel; }
                catch { copy.textContent='Selecciona y copia la dirección mostrada.'; }
            });
            extra.append(copy); $('#direccion').value=c.studio.address;
        } else if (radios[1].checked) {
            extra.append(node('h4',c.external.title),node('p',c.external.instructions));
            const inputs=[], controls=node('div',null,'form-grid'), confirmation=node('div');
            for (const f of c.external.fields) {
                const label=node('label',f.label+(f.required?' *':'')),input=node('input'); input.required=!!f.required;
                input.oninput=()=>{$('#direccion').value='';confirm.disabled=false;confirmation.replaceChildren();};
                label.append(input);controls.append(label);inputs.push(input);
            }
            const confirm=button(c.external.confirmLabel,()=>{
                if (inputs.some(input=>!input.reportValidity()))return;
                const address=inputs.map(input=>input.value.trim()).filter(Boolean).join(', ');
                confirmation.replaceChildren(node('h4',c.external.confirmTitle),node('p',c.external.confirmInstructions),node('p',address),button(c.external.confirmLabel,()=>{
                    $('#direccion').value=address;confirmation.replaceChildren(node('p',c.external.successMessage));confirm.disabled=true;
                }),button(c.external.editLabel,()=>{confirmation.replaceChildren();inputs[0]?.focus();}));
            });
            extra.append(controls,confirm,confirmation);
        }
    };
    radios.forEach(input=>input.onchange=render);
    $('#booking').addEventListener('submit',e=>{
        if (!$('#direccion').value) { e.preventDefault();e.stopImmediatePropagation();$('#booking-error').textContent=c.external.confirmTitle; }
    },true);
    render();
}
if (config.schedule) {
    let sequence=0;
    $('#booking').addEventListener('submit',e=>{
        if (!$('#times input:checked')) { e.preventDefault();e.stopImmediatePropagation();$('#booking-error').textContent='Selecciona un horario disponible.'; }
    },true);
    $('#days').addEventListener('click',async e=>{
        const day=e.target.closest('button[data-date]');if (!day||day.disabled)return;
        const token=++sequence;$('#times').textContent='Consultando horarios…';
        try {
            const response=await fetch('/api/schedule/availability?date='+encodeURIComponent(day.dataset.date));
            if (!response.ok)throw Error('No se pudo consultar la agenda.');
            const value=await response.json();if(token!==sequence)return;
            $('#times').replaceChildren();
            for (const time of value.slots) {const label=node('label',time),input=node('input');input.type='radio';input.name='hora';input.value=time;input.required=true;label.prepend(input);$('#times').append(label);}
            if(!value.slots.length)$('#times').textContent='No hay horarios disponibles para esta fecha.';
        } catch(error){if(token===sequence)$('#times').textContent=error.message;}
    });
}
