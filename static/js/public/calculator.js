import { $, money, state } from './shared.js';
import { CMS } from './content.js';
let configuredTotal;
export function setConfiguredTotal(fn) {
    configuredTotal = fn;
}

export function groupTotal() {
    if (configuredTotal) return configuredTotal();
    return (
        CMS.settings.base +
        CMS.settings.companion * state.count +
        ($('#hair').checked ? CMS.settings.hair * (state.count + 1) : 0) +
        ($('#trial').checked ? CMS.settings.trial : 0)
    );
}

function updateGroup() {
    $('#count').textContent = state.count;
    $('#minus').disabled = state.count === 0;
    $('#plus').disabled = state.count === 100;
    const rows = [['Paquete novia (base)', CMS.settings.base]];
    if (state.count)
        rows.push([
            `${state.count} acompañante${state.count === 1 ? '' : 's'}`,
            state.count * CMS.settings.companion
        ]);
    if ($('#hair').checked)
        rows.push([`Peinado (${state.count + 1} personas)`, CMS.settings.hair * (state.count + 1)]);
    if ($('#trial').checked) rows.push(['Prueba de Maquillaje Novia', CMS.settings.trial]);
    rows.push(['Total estimado', groupTotal()]);
    $('#breakdown').innerHTML = rows
        .map(([k, v]) => `<div><dt>${k}</dt><dd>${money(v)}</dd></div>`)
        .join('');
}
$('#minus').onclick = () => {
    state.count = Math.max(0, state.count - 1);
    updateGroup();
};
$('#plus').onclick = () => {
    state.count = Math.min(100, state.count + 1);
    updateGroup();
};
$('#hair').onchange = $('#trial').onchange = updateGroup;
updateGroup();
