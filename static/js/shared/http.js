/** Never expose an HTML error page as a JSON parser exception. */
export async function readJSON(response) {
    if (!(response.headers.get('content-type') || '').toLowerCase().includes('application/json')) {
        throw Error(
            'El servidor no devolvió los datos esperados (HTTP ' +
                response.status +
                '). Abre Tamara con abrir-tamara.vbs y entra desde http://127.0.0.1:8765/login.'
        );
    }
    try {
        return await response.json();
    } catch {
        throw Error('La respuesta del servidor está incompleta. Vuelve a intentarlo.');
    }
}
