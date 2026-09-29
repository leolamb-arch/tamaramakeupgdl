import { $, money, escapeHTML, modal, box, state } from './shared.js';
import { SERVICES } from './content.js';
import { openModal } from './navigation.js';
$('#catalog').innerHTML = SERVICES.map(
    (s, i) =>
        `<article class="card"><button class="cover" data-gallery="${i}" aria-label="${s.images.length ? 'Ampliar imágenes de' : 'Sin imágenes para'} ${escapeHTML(s.name)}">${s.images.length ? `<img data-image="${s.imageKeys[Math.min(s.cover_index, s.images.length - 1)]}" src="${s.images[Math.min(s.cover_index, s.images.length - 1)]}" alt="Placeholder de ${escapeHTML(s.name)}" loading="lazy"><span class="magnify" aria-hidden="true">⊕</span>${s.images.length > 1 ? `<span class="photo-count">▧ ${s.images.length} fotos</span>` : ''}` : '<span class="no-photo" aria-hidden="true">▧</span>'}</button><button class="card-details" data-service="${i}" aria-label="Ver detalles de ${escapeHTML(s.name)}"><h3>${escapeHTML(s.name)}</h3><p>${escapeHTML(s.short)}</p><span class="price">Reserva ${money(s.price_amount)}</span>${s.price ? `<span class="price-note">${escapeHTML(s.price)}</span>` : ''}<span class="details-link">Ver detalles <span>›</span></span></button></article>`
).join('');
SERVICES.forEach((s) => $('#servicio').add(new Option(s.name, s.slug)));
document
    .querySelectorAll('[data-service]')
    .forEach((b) => (b.onclick = () => showService(+b.dataset.service)));
document.querySelectorAll('[data-gallery]').forEach(
    (b) =>
        (b.onclick = () => {
            state.currentService = SERVICES[+b.dataset.gallery];
            state.photo = Math.min(
                state.currentService.cover_index,
                state.currentService.images.length - 1
            );
            if (state.currentService.images.length) showLarge();
            else showService(+b.dataset.gallery);
        })
);

function showService(i) {
    state.currentService = SERVICES[i];
    state.photo = 0;
    const s = state.currentService;
    openModal(
        `<h2 id="modal-title">${escapeHTML(s.name)}</h2><p class="dialog-description">${escapeHTML(s.description)}</p><div class="badges"><span class="primary">Reserva ${money(s.price_amount)}</span>${s.price ? `<span>${escapeHTML(s.price)}</span>` : ''}<span>${escapeHTML(s.duration)}</span></div><ul class="includes">${s.includes.map((x) => `<li>${escapeHTML(x)}</li>`).join('')}</ul><div class="gallery"><p class="eyebrow">Galería de trabajos · ${s.images.length} fotos</p>${s.images.length ? `<div class="gallery-main"><button id="enlarge" aria-label="Ampliar foto"><img id="detail-photo" data-image="${s.imageKeys[0]}" src="${s.images[0]}" alt="Placeholder de ${escapeHTML(s.name)}"></button></div><div class="gallery-controls"><button id="photo-prev" aria-label="Foto anterior">‹</button><output id="photo-count"></output><button id="photo-next" aria-label="Foto siguiente">›</button></div><div class="thumbs">${s.images.map((p, n) => `<button data-photo="${n}" aria-label="Ver foto ${n + 1}"><img data-image="${s.imageKeys[n]}" src="${p}" alt="Miniatura placeholder ${n + 1}"></button>`).join('')}</div>` : '<p class="notice">Aún no se han agregado fotografías a este servicio.</p>'}</div><a id="service-quote" class="pill primary full modal-cta" href="#cotizar">Cotizar ${escapeHTML(s.name.toLowerCase())}</a>`
    );
    if (s.images.length) {
        $('#enlarge').onclick = showLarge;
        $('#photo-prev').onclick = () => changePhoto(-1);
        $('#photo-next').onclick = () => changePhoto(1);
        document.querySelectorAll('[data-photo]').forEach(
            (b) =>
                (b.onclick = () => {
                    state.photo = +b.dataset.photo;
                    updatePhoto();
                })
        );
        updatePhoto();
        swipe($('.gallery-main'));
    }
    $('#service-quote').onclick = () => {
        $('#servicio').value = s.slug;
        modal.close();
    };
}

function updatePhoto() {
    const s = state.currentService;
    if ($('#detail-photo')) {
        $('#detail-photo').dataset.image = s.imageKeys[state.photo];
        $('#detail-photo').src = s.images[state.photo];
        $('#photo-count').textContent = `${state.photo + 1} / ${s.images.length}`;
        document
            .querySelectorAll('[data-photo]')
            .forEach((b) =>
                b.setAttribute('aria-current', String(+b.dataset.photo === state.photo))
            );
    }
    if (box.open) {
        $('#large-photo').dataset.image = s.imageKeys[state.photo];
        $('#large-photo').src = s.images[state.photo];
        $('#large-photo').alt = `Placeholder de ${s.name}, foto ${state.photo + 1}`;
        $('#large-count').textContent = `${state.photo + 1} / ${s.images.length}`;
    }
}

function changePhoto(delta) {
    state.photo =
        (state.photo + delta + state.currentService.images.length) %
        state.currentService.images.length;
    state.zoom = 1;
    $('#large-photo').style.transform = '';
    updatePhoto();
}

function showLarge() {
    state.zoom = 1;
    $('#large-photo').style.transform = '';
    box.showModal();
    updatePhoto();
}
$('#large-prev').onclick = () => changePhoto(-1);
$('#large-next').onclick = () => changePhoto(1);
$('#zoom-in').onclick = () => {
    state.zoom = Math.min(3, state.zoom + 0.5);
    $('#large-photo').style.transform = `scale(${state.zoom})`;
};
$('#zoom-out').onclick = () => {
    state.zoom = Math.max(1, state.zoom - 0.5);
    $('#large-photo').style.transform = `scale(${state.zoom})`;
};

function swipe(el) {
    let start = 0;
    el.addEventListener('touchstart', (e) => (start = e.changedTouches[0].clientX), {
        passive: true
    });
    el.addEventListener(
        'touchend',
        (e) => {
            const distance = e.changedTouches[0].clientX - start;
            if (Math.abs(distance) > 50 && state.zoom === 1) changePhoto(distance < 0 ? 1 : -1);
        },
        {
            passive: true
        }
    );
}
swipe($('.lightbox-image'));
document.addEventListener('keydown', (e) => {
    if (
        (box.open || (modal.open && $('#detail-photo'))) &&
        ['ArrowRight', 'ArrowLeft'].includes(e.key)
    ) {
        e.preventDefault();
        changePhoto(e.key === 'ArrowRight' ? 1 : -1);
    }
});
