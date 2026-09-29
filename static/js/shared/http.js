/** Never expose an HTML error page as a JSON parser exception. */
export async function readJSON(response) {
    if (!(response.headers.get('content-type') || '').toLowerCase().includes('application/json')) {
        throw Error(
            'El servidor no devolvió los datos esperados (HTTP ' +
                response.status +
                '). Recarga la página o vuelve a iniciar sesión en /login.'
        );
    }
    try {
        return await response.json();
    } catch {
        throw Error('La respuesta del servidor está incompleta. Vuelve a intentarlo.');
    }
}
