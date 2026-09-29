import {
    data,
    defaults,
    names,
    clone,
    el,
    changed,
    button,
    field,
    card,
    render,
    ask
} from './editor.js';
export function appearance() {
    const c = card('Colores y tipografías');
    const grid = el('div', undefined, 'grid');
    c.append(grid);
    Object.entries(data.theme).forEach(([k, v]) =>
        field(
            grid,
            names[k],
            v,
            (x) => (data.theme[k] = x),
            ['font', 'heading'].includes(k) ? 'select' : 'color',
            ['Outfit', 'Pinyon Script', 'Georgia', 'Arial', 'system-ui']
        )
    );
    c.append(
        button('Restaurar apariencia original', async () => {
            if (await ask('¿Restaurar los colores y tipografías originales en el borrador?')) {
                data.theme = clone(defaults.theme);
                changed();
                render();
            }
        })
    );
}
