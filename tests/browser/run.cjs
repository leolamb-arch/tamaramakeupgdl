const { chromium } = require('playwright');
const { default: AxeBuilder } = require('@axe-core/playwright');
const { spawn } = require('node:child_process');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
    const password = crypto.randomBytes(24).toString('hex');
    const port = process.env.TEST_PORT || '8877';
    const origin = 'http://127.0.0.1:' + port;
    const python =
        process.env.PYTHON ||
        (process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
    const server = spawn(python, ['-m', 'tests.browser.server'], {
        env: {
            ...process.env,
            APP_SECRET: crypto.randomBytes(48).toString('hex'),
            APP_ENV: 'development',
            APP_ORIGIN: origin,
            TRUSTED_PROXY_CIDRS: '',
            TEST_ADMIN_PASSWORD: password,
            TEST_PORT: port
        },
        stdio: ['ignore', 'pipe', 'pipe']
    });
    let browser;
    const output = path.resolve('test-results');
    fs.mkdirSync(output, { recursive: true });
    try {
        await new Promise((resolve, reject) => {
            const timer = setTimeout(
                () => reject(Error('El servidor de pruebas no arrancó.')),
                20000
            );
            server.once('error', reject);
            server.once('exit', (code) => reject(Error('Servidor terminó: ' + code)));
            server.stderr.on('data', (data) => process.stderr.write(data));
            server.stdout.on('data', (data) => {
                if (data.toString().includes('READY')) {
                    clearTimeout(timer);
                    resolve();
                }
            });
        });
        browser = await chromium.launch({
            headless: true,
            ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {})
        });
        const problems = [];
        const results = [];
        for (const [name, width, height] of [
            ['desktop', 1440, 1000],
            ['mobile', 390, 844]
        ]) {
            const context = await browser.newContext({
                viewport: { width, height },
                reducedMotion: 'reduce'
            });
            const page = await context.newPage();
            page.on('pageerror', (error) => {
                problems.push(name + ': ' + error.message);
                console.error(error.message);
            });
            page.on('response', (response) => {
                if (response.status() >= 400)
                    console.error('HTTP', response.status(), response.url());
            });
            page.on('console', (message) => {
                if (message.type() === 'error') problems.push(name + ': ' + message.text());
            });
            await page.goto(origin);
            await page.evaluate(() => document.fonts.ready);
            assert.equal((await page.locator('#catalog article').count()) > 0, true);
            assert.equal(
                await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
                true,
                'Desbordamiento horizontal ' + name
            );
            await page.screenshot({ path: path.join(output, name + '.png'), fullPage: true });
            const axe = await new AxeBuilder({ page })
                .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                .analyze();
            results.push({
                page: name,
                violations: axe.violations.map((v) => ({
                    id: v.id,
                    impact: v.impact,
                    nodes: v.nodes.map((n) => n.target)
                }))
            });
            await page.locator('[data-gallery="0"]').click();
            assert.equal(await page.locator('#lightbox').evaluate((el) => el.open), true);
            await page.keyboard.press('Escape');
            if (name === 'mobile') {
                await page.locator('#menu-open').click();
                assert.equal(await page.locator('#mobile-menu').evaluate((el) => el.open), true);
                await page.keyboard.press('Escape');
            }
            await page.locator('#nombre').fill('Cliente navegador');
            await page.locator('[name=telefono]').fill('3312345678');
            await page.locator('[name=email]').fill('cliente@example.com');
            await page.locator('#servicio').selectOption('social');
            await page.locator('[name=ubicacion]').first().check();
            const today = await page.evaluate(() => new Date().toLocaleDateString('en-CA'));
            let chosen;
            for (const day of await page
                .locator('#days button:not(:disabled)')
                .evaluateAll((nodes) => nodes.map((n) => n.dataset.date))) {
                if (day <= today) continue;
                const response = await context.request.get(
                    origin + '/api/schedule/availability?date=' + day
                );
                if ((await response.json()).slots.length) {
                    chosen = day;
                    break;
                }
            }
            if (!chosen) {
                await page.locator('#month-next').click();
                chosen = await page
                    .locator('#days button:not(:disabled)')
                    .first()
                    .getAttribute('data-date');
            }
            await page.locator(`[data-date="${chosen}"]`).click();
            await page.locator('#times input').first().check();
            await page.locator('#booking button[type=submit]').click();
            await page.locator('#send-request').click();
            await page.getByText('Solicitud enviada', { exact: true }).waitFor();
            assert.match(
                await page.locator('#request-status').textContent(),
                /pendiente de confirmación/
            );
            await page.goto(origin + '/login');
            await page.locator('input').first().fill('test-admin');
            await page.locator('input[type=password]').fill(password);
            await page.locator('button[type=submit]').click();
            await page.waitForURL(origin + '/admin');
            await page.getByRole('button', { name: 'Textos y versiones', exact: true }).click();
            await page
                .getByText('Todos los textos, imágenes y versiones', { exact: true })
                .waitFor();
            await page.getByText('Textos de todas las secciones', { exact: true }).click();
            const navigation = page
                .locator('label')
                .filter({ hasText: '[t001]' })
                .locator('textarea');
            await navigation.fill('Inicio prueba ' + name);
            await page.getByRole('button', { name: 'Guardar y publicar', exact: true }).click();
            await page.getByText('Contenido publicado correctamente.', { exact: true }).waitFor();
            const publicPage = await context.newPage();
            await publicPage.goto(origin);
            assert.match(
                await publicPage.locator('.desktop-nav').textContent(),
                new RegExp('Inicio prueba ' + name)
            );
            await publicPage.close();
            await page.getByRole('button', { name: 'Agenda', exact: true }).click();
            await page
                .getByText(/Cliente navegador/)
                .first()
                .waitFor();
            await page.screenshot({
                path: path.join(output, 'admin-' + name + '.png'),
                fullPage: true
            });
            const adminAxe = await new AxeBuilder({ page })
                .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                .analyze();
            results.push({
                page: 'admin-' + name,
                violations: adminAxe.violations.map((v) => ({
                    id: v.id,
                    impact: v.impact,
                    nodes: v.nodes.map((n) => n.target)
                }))
            });
            if (name === 'mobile') {
                for (const [tab, save] of [
                    ['Contenido', 'Guardar contenido'],
                    ['Ubicación', 'Guardar configuración de ubicación'],
                    ['Cotización y Quiz', 'Guardar cotización y quiz'],
                    ['Apariencia', 'Guardar apariencia']
                ]) {
                    await page.getByRole('button', { name: tab, exact: true }).click();
                    const button = page.getByRole('button', { name: save, exact: true });
                    await button.waitFor();
                    if (tab === 'Cotización y Quiz')
                        await page
                            .getByText('Precio base del paquete (MXN)', { exact: true })
                            .locator('..')
                            .locator('input')
                            .fill('3600');
                    console.log('Verificando pestaña:', tab);
                    const [response] = await Promise.all([
                        page.waitForResponse(
                            (response) =>
                                response.url().includes('/api/admin/reference/') &&
                                response.request().method() === 'POST',
                            { timeout: 10000 }
                        ),
                        button.click()
                    ]).catch(async (error) => {
                        console.error(
                            'ALERTAS',
                            await page.locator('[role=alert]').allTextContents()
                        );
                        await page.screenshot({
                            path: path.join(output, 'fallo.png'),
                            fullPage: true
                        });
                        throw error;
                    });
                    assert.equal(response.status(), 200, tab + ': ' + (await response.text()));
                    const audit = await new AxeBuilder({ page })
                        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                        .analyze();
                    results.push({
                        page: 'tab-' + tab,
                        violations: audit.violations.map((v) => ({
                            id: v.id,
                            impact: v.impact,
                            nodes: v.nodes.map((n) => n.target)
                        }))
                    });
                }
                await page.getByRole('button', { name: 'Textos y versiones', exact: true }).click();
                await page
                    .getByText('Colores y contraste: aplicar solo si lo deseas', { exact: true })
                    .click();
                await page
                    .getByRole('button', { name: 'Proponer contraste accesible', exact: true })
                    .click();
                await page
                    .getByText(
                        'Propuesta calculada, todavía sin publicar. Revisa la vista previa.',
                        { exact: true }
                    )
                    .waitFor();
                await page
                    .getByRole('button', { name: 'Vista previa privada', exact: true })
                    .click();
                await page
                    .getByText('Vista previa privada. La página pública no ha cambiado.', {
                        exact: true
                    })
                    .waitFor();
                await page.getByRole('button', { name: 'Guardar y publicar', exact: true }).click();
                await page
                    .getByText('Contenido publicado correctamente.', { exact: true })
                    .waitFor();
                const adjusted = await context.newPage();
                await adjusted.goto(origin);
                await adjusted.evaluate(() => document.fonts.ready);
                const audit = await new AxeBuilder({ page: adjusted })
                    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                    .analyze();
                results.push({
                    page: 'contraste-publicado',
                    violations: audit.violations.map((v) => ({
                        id: v.id,
                        impact: v.impact,
                        nodes: v.nodes.map((n) => n.target)
                    }))
                });
                await adjusted.screenshot({
                    path: path.join(output, 'contraste-opcional.png'),
                    fullPage: true
                });
                await adjusted.close();
                await page
                    .getByRole('checkbox', {
                        name: 'Mejorar contraste de este panel en este navegador',
                        exact: true
                    })
                    .check();
                await page.getByRole('button', { name: 'Agenda', exact: true }).click();
                await page
                    .getByText(/Cliente navegador/)
                    .first()
                    .waitFor();
                await page.evaluate(() =>
                    Promise.all(
                        document
                            .getAnimations()
                            .map((animation) => animation.finished.catch(() => {}))
                    )
                );
                const privateAudit = await new AxeBuilder({ page })
                    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                    .analyze();
                results.push({
                    page: 'panel-contraste-opcional',
                    violations: privateAudit.violations.map((v) => ({
                        id: v.id,
                        impact: v.impact,
                        nodes: v.nodes.map((n) => n.target)
                    }))
                });
            }
            await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
            await page.waitForURL(origin + '/login');
            assert.equal((await context.request.get(origin + '/api/admin/content')).status(), 401);
            await context.close();
        }
        fs.writeFileSync(path.join(output, 'accessibility.json'), JSON.stringify(results, null, 2));
        fs.writeFileSync(path.join(output, 'console.json'), JSON.stringify(problems, null, 2));
        assert.deepEqual(problems, [], 'Errores de consola');
        assert.deepEqual(
            results.flatMap((row) => row.violations.filter((v) => v.id !== 'color-contrast')),
            [],
            'Accesibilidad funcional'
        );
        assert.deepEqual(
            results.find((row) => row.page === 'contraste-publicado').violations,
            [],
            'Contraste propuesto en página pública'
        );
        assert.deepEqual(
            results.find((row) => row.page === 'panel-contraste-opcional').violations,
            [],
            'Contraste opcional del panel'
        );

        console.log(
            'Flujos de escritorio y móvil completados. Auditoría de accesibilidad:',
            path.join(output, 'accessibility.json')
        );
    } finally {
        await browser?.close();
        server.kill();
    }
})().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
