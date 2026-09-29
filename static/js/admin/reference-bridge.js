/** Local adapter for the reference panel. Authentication stays in HttpOnly cookies.
 * The reference SDK is not used and no data is sent to the production site.
 */
import { readJSON } from '../shared/http.js';
let session = await fetch('/api/session').then(readJSON).catch(() => ({}));
const listeners = new Set();
const versions = new Map();
async function request(path, options = {}) {
    const headers = new Headers(options.headers);
    headers.set('Accept', 'application/json');
    if (options.method && options.method !== 'GET') headers.set('X-CSRF-Token', session.csrf || '');
    const response = await fetch(path, { ...options, headers });
    const result = await readJSON(response);
    if (!response.ok) throw new Error(result.error || result.message || 'No se pudo completar la operación.');
    return result;
}
const store = {
    get record() { return session.authenticated ? { email: session.user, role: 'admin', id: 'local-admin' } : null; },
    get isValid() { return !!session.authenticated; },
    token: '',
    onChange(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    async clear() {
        try { await request('/api/admin/logout', { method: 'POST' }); }
        catch (e) { window.alert(e.message); return; }
        session = {};
        for (const fn of listeners) fn('', null);
        window.location.assign('/login');
    }
};
function track(name, record) {
    versions.set(`${name}/${record.id}`, record._version);
    return record;
}
export const client = {
    authStore: store,
    files: { getURL: (_record, filename) => filename?.startsWith('/') ? filename : '/' + (filename || '') },
    filter: (_query, values) => values.name || '',
    collection(name) {
        const base = '/api/admin/reference/' + encodeURIComponent(name);
        async function save(id, data) {
            const headers = {};
            let body;
            if (data instanceof FormData) {
                // Upload independently so a gallery is not constrained by one
                // request's total size. The existing endpoint validates images.
                body = new FormData();
                for (const [key, value] of data.entries()) {
                    if (value instanceof File) {
                        const upload = new FormData(); upload.append('file', value);
                        const result = await request('/api/admin/upload', { method: 'POST', body: upload });
                        body.append(key, result.src);
                    } else body.append(key, value);
                }
            }
            else { body = JSON.stringify(data); headers['Content-Type'] = 'application/json'; }
            if (id) headers['X-Record-Version'] = String(versions.get(`${name}/${id}`) ?? -1);
            return track(name, await request(base + (id ? '/' + encodeURIComponent(id) : ''), { method: 'POST', headers, body }));
        }
        return {
            async getFullList(options = {}) {
                const rows = await request(base);
                rows.forEach(row => track(name, row));
                return options.filter && name === 'bookings' ? rows.filter(row => row.service === options.filter) : rows;
            },
            create: data => save(null, data),
            update: (id, data) => save(id, data),
            delete: id => request(base + '/' + encodeURIComponent(id), { method: 'DELETE', headers: { 'X-Record-Version': String(versions.get(`${name}/${id}`) ?? -1) } }),
            async authWithPassword(name, password) {
                await request('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, password }) });
                session = await request('/api/session');
                for (const fn of listeners) fn('', store.record);
                window.location.assign('/admin');
                return { record: store.record };
            }
        };
    }
};
export async function localFetch(path, options = {}) {
    const headers = new Headers(options.headers);
    headers.delete('Authorization');
    if (options.method && options.method !== 'GET') headers.set('X-CSRF-Token', session.csrf || '');
    return fetch('/api/admin/reference-tools' + path, { ...options, headers });
}
