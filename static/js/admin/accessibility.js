/** Associate the existing visible field labels without changing panel styling. */
let sequence = 0;
let queued = false;
function connectLabels() {
    queued = false;
    for (const input of document.querySelectorAll('input, textarea, select, [role="combobox"]')) {
        if (
            input.labels?.length ||
            input.hasAttribute('aria-label') ||
            input.hasAttribute('aria-labelledby')
        )
            continue;
        const label = input.parentElement.querySelector(':scope > label');
        if (!label || !label.textContent.trim()) continue;
        if (input.matches('input,textarea,select')) {
            input.id ||= 'admin-control-' + ++sequence;
            label.htmlFor = input.id;
        } else {
            label.id ||= 'admin-label-' + ++sequence;
            input.setAttribute('aria-labelledby', label.id);
        }
    }
}
new MutationObserver(() => {
    if (!queued) {
        queued = true;
        requestAnimationFrame(connectLabels);
    }
}).observe(document.body, { childList: true, subtree: true });
connectLabels();

const preference = 'tamara-admin-contrast';
export function panelContrastEnabled() {
    try {
        return localStorage.getItem(preference) === 'true';
    } catch {
        return false;
    }
}
export function setPanelContrast(enabled) {
    document.documentElement.toggleAttribute('data-admin-contrast', enabled);
    try {
        localStorage.setItem(preference, String(enabled));
    } catch {
        /* Private browsing may disable storage. */
    }
}
const style = document.createElement('style');
style.textContent =
    ':root[data-admin-contrast]{--gold:38 46% 30% !important;--muted-foreground:20 18% 28% !important;--primary:346 32% 34% !important;--primary-foreground:0 0% 100% !important;}';
document.head.append(style);
setPanelContrast(panelContrastEnabled());
