/* Interacciones reconstruidas en JavaScript puro. El contenido procede del servidor; las reservas siguen siendo locales.
   Los SVG de SERVICES se usan en tarjetas (4:3), galería (4:3), miniaturas (1:1)
   y ampliación (contain). Sustituir los archivos conservando estos recortes. */
'use strict';
export const $ = (s) => document.querySelector(s);
export const money = (n) =>
    new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN'
    }).format(n);
export const escapeHTML = (s) =>
    String(s).replace(
        /[&<>"']/g,
        (c) =>
            ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            })[c]
    );
export const modal = $('#modal'),
    box = $('#lightbox');
export const state = {
    currentService: null,
    photo: 0,
    zoom: 1,
    count: 0,
    chosenDate: '',
    month: new Date()
};
state.month.setDate(1);
state.month.setHours(0, 0, 0, 0);
export const today = new Date();
today.setHours(0, 0, 0, 0);
export const dateKey = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
export const dateLabel = (d) =>
    d.toLocaleDateString('es-MX', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
