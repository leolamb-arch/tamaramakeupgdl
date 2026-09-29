/** Complete CMS editor using the panel's existing React runtime and CSS classes. */
import { adminRequest } from './reference-bridge.js';
import { suggestContrast, contrast } from './contrast.js';
import { panelContrastEnabled, setPanelContrast } from './accessibility.js';

export function createFullEditor(jsx, React) {
    const h = (tag, props, ...children) =>
        jsx.jsxs(tag, { ...props, ...(children.length ? { children } : {}) });
    const controlClass = 'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm';
    const buttonClass =
        'rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground';
    return function FullEditor() {
        const [model, setModel] = React.useState(null);
        const [history, setHistory] = React.useState([]);
        const [message, setMessage] = React.useState('');
        const [busy, setBusy] = React.useState(false);
        const [dirty, setDirty] = React.useState(false);
        const [query, setQuery] = React.useState('');
        const [preview, setPreview] = React.useState('');
        const [panelContrast, setPanelPreference] = React.useState(panelContrastEnabled);
        async function load() {
            const value = await adminRequest('/api/admin/content');
            setModel(value);
            setHistory(await adminRequest('/api/admin/history'));
            setDirty(false);
        }
        React.useEffect(() => {
            load().catch((error) => setMessage(error.message));
        }, []);
        React.useEffect(() => {
            const leave = (event) => {
                if (dirty) {
                    event.preventDefault();
                    event.returnValue = '';
                }
            };
            window.addEventListener('beforeunload', leave);
            return () => window.removeEventListener('beforeunload', leave);
        }, [dirty]);
        const change = (group, key, value) => {
            setModel((old) => ({
                ...old,
                content: { ...old.content, [group]: { ...old.content[group], [key]: value } }
            }));
            setDirty(true);
        };
        async function run(action) {
            setBusy(true);
            setMessage('');
            try {
                await action();
            } catch (error) {
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }
        const field = (label, value, onChange, maxLength = 5000) =>
            h(
                'label',
                { className: 'block text-sm', key: label },
                label,
                h('textarea', {
                    className: controlClass,
                    value,
                    maxLength,
                    rows: value.length > 100 ? 3 : 1,
                    onChange: (event) => onChange(event.target.value)
                })
            );
        if (!model) return h('p', { role: 'status' }, message || 'Cargando contenido…');
        return h(
            'section',
            { className: 'mt-4 rounded-2xl border border-border bg-card p-5' },
            h(
                'h2',
                { className: 'font-display text-lg font-semibold' },
                'Todos los textos, imágenes y versiones'
            ),
            h(
                'p',
                { className: 'text-sm text-muted-foreground' },
                'Edita los textos de cada sección. Guardar publica los cambios. Las imágenes, colores y servicios también conservan sus controles habituales.'
            ),
            h(
                'p',
                { role: 'status', 'aria-live': 'polite' },
                message || (dirty ? 'Cambios sin guardar' : '')
            ),
            h(
                'fieldset',
                { disabled: busy },
                h(
                    'label',
                    { className: 'block text-sm' },
                    'Buscar texto',
                    h('input', {
                        type: 'search',
                        className: controlClass,
                        value: query,
                        onChange: (event) => setQuery(event.target.value)
                    })
                ),
                h(
                    'label',
                    { className: 'block text-sm' },
                    h('input', {
                        type: 'checkbox',
                        checked: panelContrast,
                        onChange: (event) => {
                            setPanelPreference(event.target.checked);
                            setPanelContrast(event.target.checked);
                        }
                    }),
                    'Mejorar contraste de este panel en este navegador'
                ),
                h(
                    'details',
                    {},
                    h('summary', {}, 'Colores y contraste: aplicar solo si lo deseas'),
                    h(
                        'p',
                        { className: 'text-sm' },
                        'La propuesta ajusta únicamente los colores de texto y botones. No modifica tipografías, fondos ni distribución. Revisa la vista previa y guarda para publicarla.'
                    ),
                    ...Object.entries(model.content.theme)
                        .filter(([, value]) => /^#[0-9a-f]{6}$/i.test(value))
                        .map(([key, value]) =>
                            h(
                                'label',
                                { key, className: 'block text-sm' },
                                key,
                                h('input', {
                                    type: 'color',
                                    value,
                                    onChange: (event) => change('theme', key, event.target.value)
                                }),
                                h(
                                    'span',
                                    {},
                                    ' ' +
                                        value +
                                        (key === 'muted' || key === 'gold' || key === 'foreground'
                                            ? ' · contraste sobre fondo: ' +
                                              contrast(
                                                  value,
                                                  model.content.theme.background
                                              ).toFixed(2) +
                                              ':1'
                                            : '')
                                )
                            )
                        ),
                    h(
                        'button',
                        {
                            type: 'button',
                            className: buttonClass,
                            onClick: () => {
                                try {
                                    const theme = suggestContrast(model.content.theme);
                                    setModel((old) => ({
                                        ...old,
                                        content: { ...old.content, theme }
                                    }));
                                    setDirty(true);
                                    setMessage(
                                        'Propuesta calculada, todavía sin publicar. Revisa la vista previa.'
                                    );
                                } catch (error) {
                                    setMessage(error.message);
                                }
                            }
                        },
                        'Proponer contraste accesible'
                    )
                ),
                h(
                    'button',
                    {
                        type: 'button',
                        className: buttonClass,
                        onClick: () =>
                            run(async () => {
                                const result = await adminRequest('/api/admin/draft', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        revision: model.revision,
                                        content: model.content
                                    })
                                });
                                setModel((old) => ({ ...old, revision: result.revision }));
                                setPreview('/preview?v=' + result.revision);
                                setMessage(
                                    'Vista previa privada. La página pública no ha cambiado.'
                                );
                            })
                    },
                    'Vista previa privada'
                ),
                preview &&
                    h('iframe', {
                        title: 'Vista previa privada del sitio',
                        src: preview,
                        style: { width: '100%', height: '500px', border: 0 }
                    }),
                h(
                    'details',
                    {},
                    h('summary', {}, 'Textos de todas las secciones'),
                    ...Object.entries(model.content.texts)
                        .filter(([key, value]) =>
                            (model.labels[key] + ' ' + value)
                                .toLocaleLowerCase('es')
                                .includes(query.toLocaleLowerCase('es'))
                        )
                        .map(([key, value]) =>
                            field((model.labels[key] || key) + ' [' + key + ']', value, (value) =>
                                change('texts', key, value)
                            )
                        )
                ),
                h(
                    'details',
                    {},
                    h('summary', {}, 'Título y descripción para buscadores'),
                    field(
                        'Título SEO',
                        model.content.seo.title,
                        (value) => change('seo', 'title', value),
                        150
                    ),
                    field(
                        'Descripción SEO',
                        model.content.seo.description,
                        (value) => change('seo', 'description', value),
                        300
                    )
                ),
                h(
                    'details',
                    {},
                    h('summary', {}, 'Imágenes y textos alternativos'),
                    ...Object.entries(model.content.images).map(([key, item]) =>
                        h(
                            'div',
                            { key, className: 'mt-4' },
                            h('p', {}, key),
                            field(
                                'Texto alternativo: ' + key,
                                item.alt,
                                (alt) => change('images', key, { ...item, alt }),
                                250
                            ),
                            ...['x', 'y'].map((axis) =>
                                h(
                                    'label',
                                    { key: axis },
                                    'Enfoque ' + axis,
                                    h('input', {
                                        type: 'range',
                                        min: 0,
                                        max: 100,
                                        value: item[axis],
                                        onChange: (event) =>
                                            change('images', key, {
                                                ...item,
                                                [axis]: Number(event.target.value)
                                            })
                                    })
                                )
                            ),
                            h(
                                'label',
                                {},
                                'Reemplazar imagen',
                                h('input', {
                                    type: 'file',
                                    accept: 'image/jpeg,image/png,image/webp',
                                    onChange: (event) => {
                                        const file = event.target.files[0];
                                        if (!file) return;
                                        run(async () => {
                                            const body = new FormData();
                                            body.append('file', file);
                                            const result = await adminRequest('/api/admin/upload', {
                                                method: 'POST',
                                                body
                                            });
                                            change('images', key, { ...item, src: result.src });
                                            setMessage('Imagen cargada. Guarda para publicarla.');
                                        });
                                    }
                                })
                            )
                        )
                    )
                ),
                h(
                    'button',
                    {
                        type: 'button',
                        className: buttonClass,
                        onClick: () =>
                            run(async () => {
                                await adminRequest('/api/admin/full-content', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        revision: model.revision,
                                        content: model.content
                                    })
                                });
                                await load();
                                setMessage('Contenido publicado correctamente.');
                            })
                    },
                    'Guardar y publicar'
                ),
                h(
                    'details',
                    {},
                    h('summary', {}, 'Historial y recuperación'),
                    h(
                        'p',
                        { className: 'text-sm' },
                        'Restaurar publica esa versión del contenido. No modifica las solicitudes ni la configuración de horarios.'
                    ),
                    ...history.map((row) =>
                        h(
                            'div',
                            { key: row.id, className: 'mt-4' },
                            h(
                                'span',
                                {},
                                '#' +
                                    row.id +
                                    ' · ' +
                                    new Date(row.created * 1000).toLocaleString('es-MX') +
                                    ' · ' +
                                    row.action +
                                    ' '
                            ),
                            h(
                                'button',
                                {
                                    type: 'button',
                                    className: buttonClass,
                                    onClick: () => {
                                        if (
                                            !window.confirm(
                                                '¿Restaurar y publicar esta versión? Se sustituirán los cambios actuales.'
                                            )
                                        )
                                            return;
                                        run(async () => {
                                            await adminRequest(
                                                '/api/admin/restore-publish/' + row.id,
                                                {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({
                                                        revision: model.revision
                                                    })
                                                }
                                            );
                                            await load();
                                            setMessage('Versión restaurada y publicada.');
                                        });
                                    }
                                },
                                'Restaurar versión ' + row.id
                            )
                        )
                    )
                )
            )
        );
    };
}
