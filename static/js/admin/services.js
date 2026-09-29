import {
    data,
    editor,
    names,
    el,
    changed,
    button,
    field,
    render,
    panel,
    openPanels,
    ask,
    serviceKey
} from './editor.js';
import { photoPicker } from './images.js';
export function move(array, index, delta) {
    const next = index + delta;
    if (next < 0 || next >= array.length) return;
    [array[index], array[next]] = [array[next], array[index]];
    changed();
    render();
}

export function services() {
    editor.append(
        button('+ Crear servicio', () => {
            data.services.push({
                slug: 'servicio-' + Date.now(),
                name: 'Nuevo servicio',
                short: '',
                description: '',
                duration: '',
                price: '',
                price_amount: 0,
                includes: [],
                images: [],
                cover_index: 0,
                status: 'hidden'
            });
            openPanels.add(serviceKey(data.services.at(-1)));
            changed();
            render();
        })
    );
    data.services.forEach((s, index) => {
        const c = panel(
            s.name +
                ' · ' +
                {
                    visible: 'Visible',
                    hidden: 'Oculto',
                    archived: 'Archivado'
                }[s.status],
            serviceKey(s)
        );
        const actions = el('div', undefined, 'actions');
        actions.append(
            button('↑ Subir', () => move(data.services, index, -1)),
            button('↓ Bajar', () => move(data.services, index, 1)),
            button(
                'Archivar',
                async () => {
                    if (
                        await ask(
                            '¿Archivar este servicio? Dejará de aparecer después de publicar.'
                        )
                    ) {
                        s.status = 'archived';
                        changed();
                        render();
                    }
                },
                'danger'
            )
        );
        c.append(actions);
        const grid = el('div', undefined, 'grid');
        c.append(grid);
        for (const k of [
            'name',
            'slug',
            'short',
            'description',
            'price_amount',
            'price',
            'duration'
        ])
            field(
                grid,
                names[k],
                s[k],
                (v) => {
                    if (
                        k === 'slug' &&
                        ['novia', 'eventos', 'social', 'editorial'].includes(s.slug)
                    )
                        s.quiz_slug ||= s.slug;
                    s[k] = v;
                    if (k === 'name')
                        c.parentElement.querySelector('summary').textContent =
                            s.name +
                            ' · ' +
                            { visible: 'Visible', hidden: 'Oculto', archived: 'Archivado' }[
                                s.status
                            ];
                },
                k === 'price_amount'
                    ? 'number'
                    : ['short', 'description'].includes(k)
                      ? 'textarea'
                      : 'text'
            );
        field(
            c,
            'Estado',
            s.status,
            (v) => {
                s.status = v;
                c.parentElement.querySelector('summary').textContent =
                    s.name +
                    ' · ' +
                    { visible: 'Visible', hidden: 'Oculto', archived: 'Archivado' }[v];
            },
            'select',
            [
                ['visible', 'Visible'],
                ['hidden', 'Oculto'],
                ['archived', 'Archivado']
            ]
        );
        field(
            c,
            names.includes,
            s.includes.join('\n'),
            (v) => (s.includes = v.split('\n').filter((x) => x.trim())),
            'textarea'
        );
        c.append(el('h3', 'Galería y portada'));
        const gallery = el('div', undefined, 'gallery');
        c.append(gallery);
        s.images.forEach((key, n) => {
            const tile = el('div', undefined, 'tile' + (n === s.cover_index ? ' active' : ''));
            const img = el('img');
            img.src = data.images[key].src;
            img.alt = data.images[key].alt;
            tile.append(img);
            tile.append(
                button(n === s.cover_index ? '✓ Portada' : 'Usar de portada', () => {
                    s.cover_index = n;
                    changed();
                    render();
                })
            );
            for (const delta of [-1, 1])
                tile.append(
                    Object.assign(
                        button(delta < 0 ? '←' : '→', () => {
                            const next = n + delta;
                            if (next < 0 || next >= s.images.length) return;
                            const cover = s.images[s.cover_index];
                            [s.images[n], s.images[next]] = [s.images[next], s.images[n]];
                            s.cover_index = s.images.indexOf(cover);
                            changed();
                            render();
                        }),
                        {
                            ariaLabel:
                                delta < 0 ? 'Mover foto a la izquierda' : 'Mover foto a la derecha'
                        }
                    )
                );
            tile.append(
                button('Quitar', async () => {
                    if (await ask('¿Quitar esta foto de la galería? El archivo se conserva.')) {
                        const cover = s.images[s.cover_index];
                        s.images.splice(n, 1);
                        s.cover_index = Math.max(0, s.images.indexOf(cover));
                        changed();
                        render();
                    }
                })
            );
            gallery.append(tile);
        });
        const chooser = el('select');
        chooser.setAttribute('aria-label', 'Imagen de biblioteca para ' + s.name);
        for (const [key, v] of Object.entries(data.images)) {
            if (s.images.includes(key)) continue;
            const o = el('option', v.alt + ' · ' + key.split('/').pop());
            o.value = key;
            chooser.append(o);
        }
        c.append(
            chooser,
            button('Agregar imagen de biblioteca', () => {
                if (chooser.value) {
                    s.images.push(chooser.value);
                    changed();
                    render();
                }
            })
        );
        photoPicker(c, (src) => {
            data.images[src] = {
                src,
                alt: s.name,
                x: 50,
                y: 50
            };
            s.images.push(src);
        });
    });
}
