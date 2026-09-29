'use strict';
export const CMS = JSON.parse(document.getElementById('cms-data').textContent);
export const SERVICES = CMS.services
    .filter((s) => s.status === 'visible')
    .map((s) => ({
        ...s,
        imageKeys: s.images,
        images: s.images.map((key) => CMS.images[key].src)
    }));
