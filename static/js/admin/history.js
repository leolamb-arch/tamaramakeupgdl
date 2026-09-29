import {
    revision,
    tab,
    editor,
    el,
    message,
    api,
    button,
    card,
    exclusive,
    ask,
    load
} from './editor.js';
export async function history() {
    editor.append(
        el(
            'p',
            'Restaurar recupera una versión como borrador. Revisa y publica para aplicarla al sitio. Se muestran las últimas 100 versiones.',
            'muted'
        )
    );
    const c = card('Versiones');
    try {
        const rows = await api('admin/history');
        if (tab !== 'Historial') return;
        if (!rows.length) c.append(el('p', 'Todavía no hay cambios guardados.'));
        rows.forEach((r) => {
            const row = el('div', undefined, 'history-row');
            row.append(
                el(
                    'span',
                    '#' +
                        r.id +
                        ' · ' +
                        new Date(r.created * 1000).toLocaleString('es-MX') +
                        ' · ' +
                        {
                            draft: 'Borrador',
                            publish: 'Publicación',
                            restore: 'Restauración',
                            original: 'Original'
                        }[r.action] +
                        ' · ' +
                        r.user
                ),
                button('Restaurar', () =>
                    exclusive(async () => {
                        if (
                            await ask(
                                '¿Reemplazar el borrador actual con esta versión? Los cambios sin guardar se perderán.'
                            )
                        ) {
                            await api('admin/restore/' + r.id, {
                                revision
                            });
                            await load();
                            message('Versión restaurada como borrador.');
                        }
                    })
                )
            );
            c.append(row);
        });
    } catch (e) {
        message(e.message);
    }
}
