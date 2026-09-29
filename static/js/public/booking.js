import { $, money, escapeHTML, modal, state, today, dateKey, dateLabel } from './shared.js';
import { SERVICES } from './content.js';
import { openModal, info } from './navigation.js';
function renderCalendar() {
    const year = state.month.getFullYear(),
        m = state.month.getMonth();
    $('#month').textContent = state.month.toLocaleDateString('es-MX', {
        month: 'long',
        year: 'numeric'
    });
    $('#month-prev').disabled = year === today.getFullYear() && m === today.getMonth();
    const first = new Date(year, m, 1),
        offset = (first.getDay() + 6) % 7,
        days = new Date(year, m + 1, 0).getDate(),
        cells = Math.ceil((offset + days) / 7) * 7;
    $('#days').innerHTML = Array.from(
        {
            length: cells
        },
        (_, i) => {
            const d = new Date(year, m, i - offset + 1),
                key = dateKey(d);
            return `<button type="button" data-date="${key}" aria-label="${dateLabel(d)}" aria-pressed="${key === state.chosenDate}" class="${d.getMonth() !== m ? 'other-month ' : ''}${key === state.chosenDate ? 'selected ' : ''}${key === dateKey(today) ? 'today' : ''}" ${d < today ? 'disabled' : ''}>${d.getDate()}</button>`;
        }
    ).join('');
    $('#days')
        .querySelectorAll('button')
        .forEach(
            (b) =>
                (b.onclick = () => {
                    state.chosenDate = b.dataset.date;
                    $('#selected-date').textContent =
                        `Fecha propuesta: ${dateLabel(new Date(state.chosenDate + 'T12:00:00'))}. Sin verificar disponibilidad.`;
                    renderCalendar();
                })
        );
}
$('#month-prev').onclick = () => {
    state.month.setMonth(state.month.getMonth() - 1);
    renderCalendar();
};
$('#month-next').onclick = () => {
    state.month.setMonth(state.month.getMonth() + 1);
    renderCalendar();
};
renderCalendar();
$('#times').innerHTML = Array.from(
    {
        length: 10
    },
    (_, i) => {
        const time = String(i + 9).padStart(2, '0') + ':00';
        return `<label><input type="radio" name="hora" value="${time}" required>${time}</label>`;
    }
).join('');
document.querySelectorAll('[name=ubicacion]').forEach(
    (r) =>
        (r.onchange = () => {
            const other = r.value === 'Otra ubicación';
            $('#address-wrap').hidden = !other;
            $('#direccion').required = other;
        })
);
$('#booking').addEventListener('submit', (e) => {
    e.preventDefault();
    if (!state.chosenDate) {
        $('#booking-error').textContent = 'Selecciona una fecha propuesta antes de continuar.';
        $('#days button:not(:disabled)').focus();
        return;
    }
    $('#booking-error').textContent = '';
    const d = new FormData(e.currentTarget),
        s = SERVICES.find((x) => x.slug === d.get('servicio'));
    if (!s) {
        info(
            'Servicios',
            'Este servicio no está publicado por ahora. Consulta el catálogo o contáctanos.'
        );
        return;
    }
    const rows = [
        ['Nombre', d.get('nombre')],
        ['Teléfono', d.get('telefono')],
        ['Correo', d.get('email') || 'No indicado'],
        ['Servicio', s.name],
        ['Personas', d.get('personas')],
        ['Ubicación', d.get('ubicacion')],
        ['Fecha propuesta', state.chosenDate],
        ['Hora propuesta', d.get('hora')],
        ['Importe de referencia', money(s.price_amount * Number(d.get('personas')))]
    ];
    if (d.get('ubicacion') === 'Otra ubicación') rows.push(['Dirección', d.get('direccion')]);
    if (d.get('comentarios')) rows.push(['Comentarios', d.get('comentarios')]);
    openModal(
        `<h2 id="modal-title">Resumen de tu solicitud</h2><p class="notice">Borrador local. No se ha enviado una solicitud ni reservado una fecha.</p><dl class="summary-list">${rows.map(([k, v]) => `<div><dt>${escapeHTML(k)}</dt><dd>${escapeHTML(v)}</dd></div>`).join('')}</dl><p>El anticipo y la confirmación necesitan una agenda y una pasarela de pago conectadas. El importe es orientativo.</p><button class="pill primary full" disabled>Pago de anticipo no disponible</button><button class="pill full" id="edit-booking">Volver a mis datos</button>`
    );
    $('#edit-booking').onclick = () => modal.close();
});
