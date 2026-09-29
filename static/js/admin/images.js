import {
    data,
    defaults,
    csrf,
    editor,
    clone,
    el,
    message,
    changed,
    button,
    field,
    card,
    render,
    exclusive,
    ask,
    previewURLs
} from './editor.js';
import { readJSON } from '../shared/http.js';
export async function upload(file) {
    if (!file) throw Error('Selecciona una fotografía.');
    if (file.size > 8 * 1024 * 1024) throw Error('Máximo 8 MB por imagen.');
    const form = new FormData();
    form.append('file', file);
    const r = await fetch('/api/admin/upload', {
        method: 'POST',
        headers: {
            'X-CSRF-Token': csrf
        },
        body: form
    });
    const result = await readJSON(r);
    if (!r.ok) throw Error(result.error);
    return result.src;
}

export function photoPicker(parent, onUploaded) {
    const label = el('label', 'Subir fotografía JPEG, PNG o WebP (máximo 8 MB)');
    const input = el('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/png,image/webp';
    label.append(input);
    parent.append(label);
    const preview = el('img');
    preview.hidden = true;
    preview.alt = 'Vista previa de la imagen seleccionada';
    preview.style.maxWidth = '240px';
    parent.append(preview);
    let url;
    input.onchange = () => {
        if (url) {
            URL.revokeObjectURL(url);
            previewURLs.delete(url);
        }
        preview.hidden = true;
        const f = input.files[0];
        if (f) {
            url = URL.createObjectURL(f);
            previewURLs.add(url);
            preview.src = url;
            preview.hidden = false;
        }
    };
    parent.append(
        button('Cargar imagen seleccionada', () =>
            exclusive(async () => {
                const src = await upload(input.files[0]);
                await onUploaded(src);
                changed();
                message(
                    'Imagen cargada de forma privada. Guarda y publica para mostrarla en el sitio.'
                );
                render();
            })
        )
    );
}

export function images() {
    editor.append(
        el(
            'p',
            'Ajusta el texto alternativo y el punto de enfoque. El recorte conserva las proporciones del sitio.',
            'muted'
        )
    );
    Object.entries(data.images).forEach(([key, v]) => {
        const c = card('');
        c.classList.add('image-card');
        const left = el('div');
        const img = el('img');
        img.src = v.src;
        img.alt = v.alt;
        img.style.objectPosition = v.x + '% ' + v.y + '%';
        left.append(img, el('small', key));
        const right = el('div');
        c.append(left, right);
        field(right, 'Texto alternativo', v.alt, (x) => {
            v.alt = x;
            img.alt = x;
        });
        for (const axis of ['x', 'y']) {
            const i = field(
                right,
                'Enfoque ' + (axis === 'x' ? 'horizontal' : 'vertical') + ' (%)',
                v[axis],
                (x) => {
                    v[axis] = Number(x);
                    img.style.objectPosition = v.x + '% ' + v.y + '%';
                },
                'range'
            );
            i.min = 0;
            i.max = 100;
        }
        photoPicker(right, (src) => (v.src = src));
        if (defaults.images[key])
            right.append(
                button('Restaurar placeholder', async () => {
                    if (await ask('¿Restaurar este placeholder en el borrador?')) {
                        data.images[key] = clone(defaults.images[key]);
                        changed();
                        render();
                    }
                })
            );
    });
    const c = card('Agregar a la biblioteca');
    photoPicker(
        c,
        (src) =>
            (data.images[src] = {
                src,
                alt: 'Fotografía',
                x: 50,
                y: 50
            })
    );
    c.append(
        el(
            'p',
            'Los archivos se conservan para que el historial siempre pueda restaurarse. Puedes reutilizarlos en las galerías.',
            'muted'
        )
    );
}
