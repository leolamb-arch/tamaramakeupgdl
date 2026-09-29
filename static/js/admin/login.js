import { readJSON } from '../shared/http.js';
let csrf = '';
const submit = document.querySelector('#login button');
submit.disabled = true;
fetch('/api/session')
    .then(async (r) => {
        const body = await readJSON(r);
        if (!r.ok) throw Error(body.error);
        return body;
    })
    .then((s) => {
        csrf = s.csrf;
        submit.disabled = false;
        if (s.authenticated) location.replace('/admin');
    })
    .catch(
        (error) =>
            (document.getElementById('message').textContent =
                error.message || 'No se pudo conectar con el servidor.')
    );
document.getElementById('login').onsubmit = async (e) => {
    e.preventDefault();
    const button = e.target.querySelector('button');
    button.disabled = true;
    try {
        const r = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf
            },
            body: JSON.stringify(Object.fromEntries(new FormData(e.target)))
        });
        const result = await readJSON(r);
        if (!r.ok) throw Error(result.error);
        location.replace('/admin');
    } catch (err) {
        document.getElementById('message').textContent = err.message;
    } finally {
        button.disabled = false;
    }
};
