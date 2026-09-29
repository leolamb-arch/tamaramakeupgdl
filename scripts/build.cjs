/** The frontend is native ES modules: verify the shipped files without restyling. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
function walk(directory) {
    return fs
        .readdirSync(directory, { withFileTypes: true })
        .flatMap((entry) =>
            entry.isDirectory()
                ? walk(path.join(directory, entry.name))
                : [path.join(directory, entry.name)]
        );
}
const files = ['static', 'templates', 'content'].flatMap((folder) => walk(path.join(root, folder)));
const manifest = {};
for (const file of files) {
    if (file.endsWith('.js')) execFileSync(process.execPath, ['--check', file], { stdio: 'pipe' });
    if (file.endsWith('.json')) JSON.parse(fs.readFileSync(file, 'utf8'));
    manifest[path.relative(root, file).replaceAll('\\', '/')] = crypto
        .createHash('sha256')
        .update(fs.readFileSync(file))
        .digest('hex');
}
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(
    path.join(root, 'dist/build-manifest.json'),
    JSON.stringify(manifest, null, 2) + '\n'
);
console.log(
    `Build verificado: ${files.length} archivos; módulos JavaScript y JSON válidos. CSS, fuentes e imágenes conservados.`
);
