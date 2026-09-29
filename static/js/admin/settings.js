import { data, names, el, field, card } from './editor.js';
export function settings() {
    const groups = [
        [
            'WhatsApp',
            ['contactWhatsapp', 'whatsapp'],
            'Usa números internacionales sin + ni espacios.'
        ],
        [
            'Redes sociales',
            ['instagram', 'facebook', 'tiktok'],
            'Usa enlaces HTTPS. Deja una red vacía para conservar el aviso pendiente.'
        ],
        [
            'Precios de la calculadora',
            ['base', 'companion', 'hair', 'trial'],
            'Importes en pesos mexicanos (MXN).'
        ]
    ];
    const known = groups.flatMap(([, keys]) => keys);
    const extra = Object.keys(data.settings).filter((k) => !known.includes(k));
    if (extra.length) groups.push(['Otros ajustes', extra, '']);
    groups.forEach(([title, keys, hint]) => {
        const c = card(title);
        c.append(el('p', hint, 'muted'));
        const grid = el('div', undefined, 'grid');
        c.append(grid);
        keys.filter((k) => k in data.settings).forEach((k) =>
            field(
                grid,
                names[k] || k,
                data.settings[k],
                (x) => (data.settings[k] = x),
                typeof data.settings[k] === 'number' ? 'number' : 'text'
            )
        );
    });
}
