/** WCAG sRGB contrast suggestions. This module never publishes changes. */
function rgb(hex) {
    return [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
}
function luminance(hex) {
    const values = rgb(hex).map((value) => {
        const channel = value / 255;
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
    return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
}
export function contrast(a, b) {
    const first = luminance(a),
        second = luminance(b);
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}
function adjust(color, backgrounds) {
    if (backgrounds.every((background) => contrast(color, background) >= 4.5)) return color;
    const channels = rgb(color);
    for (let step = 1; step <= 100; step++) {
        for (const target of [0, 255]) {
            const candidate =
                '#' +
                channels
                    .map((value) =>
                        Math.round(value + ((target - value) * step) / 100)
                            .toString(16)
                            .padStart(2, '0')
                    )
                    .join('');
            if (backgrounds.every((background) => contrast(candidate, background) >= 4.5))
                return candidate;
        }
    }
    throw Error(
        'Los fondos son demasiado distintos para una única tinta accesible. Ajusta los colores manualmente y vuelve a comprobarlos.'
    );
}
export function suggestContrast(theme) {
    const next = { ...theme };
    const backgrounds = [theme.background, theme.secondary, '#ffffff'];
    for (const key of ['foreground', 'muted', 'gold', 'primary'])
        next[key] = adjust(theme[key], backgrounds);
    return next;
}
