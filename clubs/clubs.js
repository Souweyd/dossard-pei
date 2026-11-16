/* Clubs péi — annuaire des clubs (dossardpei.re/clubs/) */
(function () {
  'use strict';
  var WEB3_KEY = '2b5c040f-3abd-4227-b2db-786027df41b1';
  var SPRITE = 'logos.webp?v=1';
  var TYPES = ['Athlétisme', 'Athlé + trail', 'Trail', 'Trail + rando', 'Multisport'];
  var COL = { 'Athlétisme': '#9fb0c0', 'Athlé + trail': '#a98bf0', 'Trail': '#66bb6a', 'Trail + rando': '#e0a458', 'Multisport': '#4fb0f0' };
  var KEYT = { 'Athlétisme': 'X', 'Athlé + trail': 'A', 'Trail': 'T', 'Trail + rando': 'H', 'Multisport': 'M' };
  var SECTS = ['Nord', 'Est', 'Ouest', 'Sud'];
  var CO = { 'Saint-Denis': [-20.88, 55.45], 'Sainte-Marie': [-20.90, 55.53], 'Sainte-Suzanne': [-20.91, 55.60], 'Saint-André': [-20.96, 55.65], 'Bras-Panon': [-21.00, 55.68], 'Saint-Benoît': [-21.03, 55.71], 'La Plaine-des-Palmistes': [-21.13, 55.63], 'Salazie': [-21.03, 55.54], 'Saint-Paul': [-21.01, 55.27], 'Le Port': [-20.94, 55.30], 'La Possession': [-20.93, 55.34], 'Saint-Leu': [-21.17, 55.29], 'Les Trois-Bassins': [-21.10, 55.31], 'Les Avirons': [-21.24, 55.34], "L'Étang-Salé": [-21.27, 55.37], 'Saint-Louis': [-21.29, 55.42], 'Saint-Pierre': [-21.33, 55.48], 'Le Tampon': [-21.24, 55.55], 'Entre-Deux': [-21.23, 55.47], 'Petite-Île': [-21.35, 55.56], 'Saint-Joseph': [-21.37, 55.62], 'Saint-Philippe': [-21.36, 55.77], 'Sainte-Rose': [-21.13, 55.79], 'Cilaos': [-21.13, 55.47] };
  var ICO = {
    T: '<path d="M2 20 L9 8 L13 14 L16 10 L22 20 Z"/>',
    A: '<ellipse cx="12" cy="15" rx="9.5" ry="5"/><path d="M6 13 L11 5 L14 9 L16 7 L19 13"/>',
    X: '<ellipse cx="12" cy="12" rx="10" ry="6"/><ellipse cx="12" cy="12" rx="5.5" ry="2.6"/>',
    H: '<path d="M2 20 L9 8 L13 14 L16 10 L22 20 Z"/><path d="M8 20 C10 17 12 18 13 15" stroke-dasharray="1.6 1.8"/>',
    M: '<circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="M6 16 L10 9 L15 9 L18 16 M10 9 L13 16 L15 9"/>'
  };
  var NET = {
    fb: { l: 'Page Facebook', b: 1, s: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#1877f2"/><path d="M13.4 20v-6.3h2.1l.3-2.5h-2.4V9.7c0-.7.2-1.2 1.2-1.2h1.3V6.3c-.2 0-1-.1-1.9-.1-1.9 0-3.2 1.2-3.2 3.3v1.8H8.7v2.5h2.1V20z" fill="#fff"/></svg>' },
    ig: { l: 'Instagram', b: 1, s: '<svg viewBox="0 0 24 24" aria-hidden="true"><defs><linearGradient id="igg" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#feda75"/><stop offset=".5" stop-color="#d62976"/><stop offset="1" stop-color="#4f5bd5"/></linearGradient></defs><rect x="2" y="2" width="20" height="20" rx="6" fill="url(#igg)"/><rect x="6.5" y="6.5" width="11" height="11" rx="3.5" fill="none" stroke="#fff" stroke-width="1.8"/><circle cx="12" cy="12" r="2.6" fill="none" stroke="#fff" stroke-width="1.8"/><circle cx="16.3" cy="7.7" r="1" fill="#fff"/></svg>' },
    strava: { l: 'Club Strava', b: 1, s: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#fc4c02"/><path d="M10.6 5.5l-4 7.8h2.4l1.6-3.1 1.6 3.1h2.4zM14.2 13.3l-1.2 2.4-1.2-2.4h-1.8l3 5.7 3-5.7z" fill="#fff"/></svg>' },
    wa: { l: 'WhatsApp', b: 1, s: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#25d366"/><path d="M7 17.2l.8-2.6a5.3 5.3 0 1 1 2 1.9z" fill="none" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M10 9.4c.2-.4.6-.4.8 0l.4.9c.1.2 0 .4-.2.6l-.3.3c.4.8 1 1.4 1.8 1.8l.3-.3c.2-.2.4-.3.6-.2l.9.4c.4.2.4.6 0 .8-.6.5-1.3.6-2 .3a6 6 0 0 1-2.6-2.6c-.3-.7-.2-1.4.3-2z" fill="#fff"/></svg>' },
    web: { l: 'Site', s: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.7 5.6 3.7 9s-1.2 6.4-3.7 9c-2.5-2.6-3.7-5.6-3.7-9S9.5 5.6 12 3z"/></svg>' },
    mail: { l: 'Écrire au club', s: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6.5L20.5 7"/></svg>' },
    tel: { l: 'Appeler le club', s: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M6.6 3.5h2.6l1.5 4-2 1.3a11 11 0 0 0 6.5 6.5l1.3-2 4 1.5v2.6c0 1.1-.9 2-2 2A16.5 16.5 0 0 1 4.6 5.5c0-1.1.9-2 2-2z"/></svg>' },
    pin: { s: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>' },
    run: { s: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="12" rx="9" ry="5.5"/><ellipse cx="12" cy="12" rx="4.5" ry="2"/></svg>' }
  };
  var ARROW = '<svg aria-hidden="true" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7"/><path d="M9 7h8v8"/></svg>';

  var $ = function (s) { return document.querySelector(s); };
  var DATA = null, POS = {};
  var st = { q: '', sect: '', type: '', commune: '', ffa: '', near: null };

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fold(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function baseCommune(c) { var k = Object.keys(CO); for (var i = 0; i < k.length; i++) if (c.indexOf(k[i]) === 0) return k[i]; return c.replace(/\s*\(.*$/, ''); }
  function km(a, b) { var R = 6371, dLa = (b[0] - a[0]) * Math.PI / 180, dLo = (b[1] - a[1]) * Math.PI / 180, x = Math.sin(dLa / 2) * Math.sin(dLa / 2) + Math.cos(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * Math.sin(dLo / 2) * Math.sin(dLo / 2); return 2 * R * Math.asin(Math.sqrt(x)); }
  function icoUrl(k, stroke, w, op) { return 'url("data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + stroke + '" stroke-width="' + w + '" stroke-opacity="' + op + '" stroke-linejoin="round" stroke-linecap="round">' + ICO[k] + '</svg>') + '")'; }
  function spriteStyle(key, size) {
    var p = POS[key], f = size / DATA.sprite.tile;
    return 'background-image:url(' + SPRITE + ');background-size:' + Math.round(DATA.sprite.w * f) + 'px ' + Math.round(DATA.sprite.h * f) + 'px;background-position:-' + Math.round(p[0] * f) + 'px -' + Math.round(p[1] * f) + 'px';
  }
  function telHref(t) { return 'tel:+262' + String(t).split('/')[0].replace(/\D/g, '').replace(/^0/, ''); }
  function maps(q) { return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(q); }
  function letter(n) { var l = fold(n).replace(/[^a-z0-9]/g, '').charAt(0).toUpperCase() || '#'; return /[0-9]/.test(l) ? '0-9' : l; }

  /* ---------- liste ---------- */
  function filtered() {
    var q = fold(st.q).trim();
    return DATA.clubs.filter(function (c) {
      if (st.sect && c.secteur !== st.sect) return false;
      if (st.type && c.type !== st.type) return false;
      if (st.commune && baseCommune(c.commune) !== st.commune) return false;
      if (st.ffa !== '' && String(+c.ffa) !== st.ffa) return false;
      if (q && fold([c.nom, c.complet, c.commune, c.type, c.courses.join(' ')].join(' ')).indexOf(q) < 0) return false;
      return true;
    });
  }
  function nets(c) {
    var h = '';
    c.reseaux.forEach(function (r) { var n = NET[r.t] || NET.web; h += '<a class="net' + (n.b ? ' brand' : '') + '" href="' + esc(r.url) + '" target="_blank" rel="noopener" aria-label="' + esc(n.l + ' de ' + c.nom) + '" title="' + esc(n.l) + '">' + n.s + '</a>'; });
    if (c.mail) h += '<a class="net" href="mailto:' + esc(c.mail) + '" aria-label="' + esc('Écrire à ' + c.nom) + '" title="E-mail">' + NET.mail.s + '</a>';
    if (c.tel) h += '<a class="net" href="' + telHref(c.tel) + '" aria-label="' + esc('Appeler ' + c.nom) + '" title="Téléphone">' + NET.tel.s + '</a>';
    return h;
  }
  function banner(c, big) {
    var col = COL[c.type];
    if (c.logo && POS[c.logo]) return '<div class="ban haslogo" aria-hidden="true"><div class="blur" style="' + spriteStyle(c.logo, 340) + '"></div></div>';
    return '<div class="ban" aria-hidden="true"><span class="ico" style="background:' + icoUrl(KEYT[c.type], '#0d1626', 1.4, 0.3) + ' center/contain no-repeat"></span></div>';
  }
  function medal(c, size) {
    if (c.logo && POS[c.logo]) return '<span class="med logo" aria-hidden="true" style="' + spriteStyle(c.logo, size - 8) + ';background-origin:padding-box"></span>';
    return '<span class="med" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="#10201a" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">' + ICO[KEYT[c.type]] + '</svg></span>';
  }
  function ind(c) {
    var h = '', soc = c.reseaux.some(function (r) { return r.t !== 'web'; }), web = c.site || c.reseaux.some(function (r) { return r.t === 'web'; });
    if (web) h += '<span class="ind" title="Site">' + NET.web.s + '</span>';
    if (soc) h += '<span class="ind" title="Réseaux"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 10.8l7.6-3.6M8.2 13.2l7.6 3.6"/></svg></span>';
    if (c.tel) h += '<span class="ind" title="Téléphone">' + NET.tel.s + '</span>';
    if (c.mail) h += '<span class="ind" title="E-mail">' + NET.mail.s + '</span>';
    if (c.adresse || c.entrainement) h += '<span class="ind" title="Adresse">' + NET.pin.s + '</span>';
    return h;
  }
  function card(c) {
    var d = st.near && c._d != null ? '<span class="dist">' + (c._d < 1 ? 'moins d’1 km' : Math.round(c._d) + ' km') + '</span>' : '';
    var i = ind(c);
    return '<article class="card" style="--c:' + COL[c.type] + '">' + banner(c) +
      '<div class="medrow">' + medal(c, 72) + '<span>' + d + (c.ffa ? ' <span class="tagffa">FFA</span>' : '') + '</span></div>' +
      '<div class="body"><h3><a href="#' + esc(c.id) + '">' + esc(c.nom) + '</a></h3>' +
      (c.complet ? '<p class="full">' + esc(c.complet) + '</p>' : '') +
      '<p class="com">' + esc(c.commune) + '</p>' +
      '<div class="inds">' + (i ? '<span class="sr">Dans la fiche : </span>' + i : '<span class="none">Contact à venir</span>') + '</div></div></article>';
  }
  function render() {
    var list = filtered();
    var html = '';
    if (st.near) {
      list.forEach(function (c) { var p = CO[baseCommune(c.commune)]; c._d = p ? km(st.near, p) : 999; });
      list.sort(function (a, b) { return a._d - b._d || a.nom.localeCompare(b.nom, 'fr'); });
      if (list.length) html = '<section class="grp"><h2>Les plus proches <small>' + list.length + ' clubs</small></h2><div class="grid">' + list.map(card).join('') + '</div></section>';
    } else {
      list.sort(function (a, b) { return a.nom.localeCompare(b.nom, 'fr', { sensitivity: 'base' }); });
      var groups = [];
      list.forEach(function (c) { var L = letter(c.nom), g = groups[groups.length - 1]; if (!g || g.l !== L) { g = { l: L, c: [] }; groups.push(g); } g.c.push(c); });
      html = groups.map(function (g) { return '<section class="grp" aria-label="Clubs en ' + g.l + '"><h2>' + g.l + ' <small>' + g.c.length + (g.c.length > 1 ? ' clubs' : ' club') + '</small></h2><div class="grid">' + g.c.map(card).join('') + '</div></section>'; }).join('');
    }
    $('#list').innerHTML = html || '<p class="empty">Aucun club ne correspond. Essaie un autre nom ou une autre commune.</p>';
    var nf = (st.sect ? 1 : 0) + (st.type ? 1 : 0) + (st.commune ? 1 : 0) + (st.ffa !== '' ? 1 : 0);
    var b = $('#f-count'); b.hidden = !nf; b.textContent = nf;
    var s = '<span class="pill">' + list.length + (list.length > 1 ? ' clubs' : ' club') + '</span>';
    if (st.commune) s += '<button type="button" class="pill" data-clear="commune">' + esc(st.commune) + ' <span aria-hidden="true">✕</span><span class="sr">Retirer ce filtre</span></button>';
    if (nf || st.q || st.near) s += '<button type="button" class="clear" data-clear="all">✕ Effacer les filtres</button>';
    $('#state').innerHTML = s;
    $('#fshow').textContent = 'Voir ' + list.length + (list.length > 1 ? ' clubs' : ' club');
    $('#near').setAttribute('aria-pressed', st.near ? 'true' : 'false');
  }

  /* ---------- filtres ---------- */
  function chipsFor(el, vals, key) {
    el.innerHTML = vals.map(function (v) { return '<button type="button" class="chip" aria-pressed="' + (st[key] === v) + '" data-k="' + key + '" data-v="' + esc(v) + '">' + (key === 'type' ? '<i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:' + COL[v] + '"></i>' : '') + esc(v) + '</button>'; }).join('');
  }
  function syncFilters() {
    chipsFor($('#fsect'), SECTS, 'sect'); chipsFor($('#ftype'), TYPES, 'type');
    $('#fcommune').value = st.commune; $('#fffa').value = st.ffa;
  }
  function fillCommunes() {
    var counts = {};
    DATA.clubs.forEach(function (c) { var b = baseCommune(c.commune); counts[b] = (counts[b] || 0) + 1; });
    Object.keys(counts).sort(function (a, b) { return a.localeCompare(b, 'fr'); }).forEach(function (k) { var o = document.createElement('option'); o.value = k; o.textContent = k + ' (' + counts[k] + ')'; $('#fcommune').appendChild(o); });
  }

  /* ---------- fiche ---------- */
  function openClub(id) {
    var c = DATA.clubs.filter(function (x) { return x.id === id; })[0];
    if (!c) return;
    var IOS = /iP(hone|ad|od)/.test(navigator.userAgent);
    function row(label, val, href, icon, go, menu) {
      var inner = '<svg class="pin" viewBox="0 0 24 24" aria-hidden="true">' + icon + '</svg><span class="go-l"><small>' + label + '</small><b>' + esc(val) + '</b></span><span class="go-go' + (go.st ? ' st' : '') + '" aria-hidden="true"><svg viewBox="0 0 24 24">' + go.p + '</svg></span>';
      if (menu) return '<div class="go"><button type="button" class="go-b" aria-haspopup="true" aria-expanded="false" aria-label="Itinéraire : ' + esc(val) + '">' + inner + '</button><div class="go-m" hidden>' + menu.map(function (m) { return '<a href="' + m[1] + '" target="_blank" rel="noopener">' + m[0] + '</a>'; }).join('') + '</div></div>';
      return '<div class="go"><a class="go-b" href="' + href + '">' + inner + '</a></div>';
    }
    function itin(q) { var e = encodeURIComponent(q), m = [['Google Maps', 'https://www.google.com/maps/dir/?api=1&destination=' + e], ['Waze', 'https://waze.com/ul?q=' + e + '&navigate=yes']]; if (IOS) m.unshift(['Plans (Apple)', 'https://maps.apple.com/?daddr=' + e]); return m; }
    var PIN = '<path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.6"/>', ARR = { p: '<path d="M3 11 21 3l-8 18-2-8z"/>' };
    var pr = '';
    if (c.adresse) pr += row('Adresse du club', c.adresse, '', PIN, ARR, itin(c.adresse + ', La Réunion'));
    if (c.entrainement) pr += row('Lieu d’entraînement', c.entrainement, '', '<ellipse cx="12" cy="12" rx="9" ry="5.5"/><ellipse cx="12" cy="12" rx="4.5" ry="2"/>', ARR, itin(c.entrainement + ', ' + baseCommune(c.commune) + ', La Réunion'));
    if (c.mail) pr += row('E-mail', c.mail, 'mailto:' + esc(c.mail), '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6.5L20.5 7"/>', { st: 1, p: '<rect x="4" y="6.5" width="16" height="11" rx="1.5"/><path d="M4.5 8l7.5 5.5L19.5 8"/>' });
    if (c.tel) pr += row('Téléphone', c.tel, telHref(c.tel), '<path d="M6.6 3.5h2.6l1.5 4-2 1.3a11 11 0 0 0 6.5 6.5l1.3-2 4 1.5v2.6c0 1.1-.9 2-2 2A16.5 16.5 0 0 1 4.6 5.5c0-1.1.9-2 2-2z"/>', { st: 1, p: '<path d="M7.2 4.5h2.2l1.3 3.4-1.7 1.1a9.3 9.3 0 0 0 5.5 5.5l1.1-1.7 3.4 1.3v2.2c0 .9-.8 1.7-1.7 1.7A14 14 0 0 1 5.5 6.2c0-.9.8-1.7 1.7-1.7z"/>' });
    var links = (c.site ? '<a class="site" href="' + esc(c.site) + '" target="_blank" rel="noopener">' + (c.siteLabel === 'Site' ? 'Site du club' : esc(c.siteLabel)) + ARROW + '</a>' : '') + c.reseaux.map(function (r) { var n = NET[r.t] || NET.web; return '<a class="net' + (n.b ? ' brand' : '') + '" href="' + esc(r.url) + '" target="_blank" rel="noopener" aria-label="' + esc(n.l) + '" title="' + esc(n.l) + '">' + n.s + '</a>'; }).join('');
    $('#club').innerHTML = '<div class="fiche" style="--c:' + COL[c.type] + ';position:relative">' +
      '<button type="button" class="x fx" data-close aria-label="Fermer">✕</button>' + banner(c) +
      '<div class="medrow">' + medal(c, 88) + (c.ffa ? '<span class="tagffa">Affilié FFA</span>' : '<span></span>') + '</div>' +
      '<div class="fin"><h2>' + esc(c.nom) + '</h2>' + (c.complet ? '<p class="meta">' + esc(c.complet) + '</p>' : '') +
      '<p class="meta">' + esc(c.type) + ' · ' + esc(c.commune) + ' · ' + esc(c.secteur) + '</p>' +
      (links ? '<div class="acts" style="margin-top:14px">' + links + '</div>' : '') +
      '<h3>Infos pratiques</h3>' + (pr ? '<div class="prat">' + pr + '</div><p class="note">Coordonnées publiées par le club (page Facebook, site ou annuaire de la FFA).</p>' : '<p class="none">Pas encore de coordonnées pour ce club. Tu les connais ? <button type="button" class="link" data-fix="' + esc(c.id) + '">Envoie-les nous</button></p>') +
      (c.courses.length ? '<h3>Courses organisées</h3><ul class="races">' + c.courses.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' : '') +
      '<p style="margin-top:18px"><button type="button" class="link" data-fix="' + esc(c.id) + '">Une info à corriger ?</button></p></div></div>';
    var d = $('#dclub'); if (!d.open) d.showModal();
    document.title = c.nom + ' – Clubs péi – Dossard Péi';
    if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: '/clubs/' + c.id, title: c.nom, event: false });
  }
  function closeDlg(d, then) {
    if (!d.open || d.classList.contains('out')) return;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { d.close(); if (then) then(); return; }
    d.classList.add('out');
    setTimeout(function () { d.classList.remove('out'); d.close(); if (then) then(); }, 220);
  }
  function closeClub() { closeDlg($('#dclub')); }
  function onHash() { var id = decodeURIComponent(location.hash.slice(1)); if (id && id !== 'ajouter') openClub(id); else closeClub(); }

  /* ---------- formulaires ---------- */
  function f(id, label, type, ph, req, hint) { return '<div class="f"><label for="' + id + '">' + label + (req ? ' *' : '') + '</label><input id="' + id + '" name="' + id + '" type="' + (type || 'text') + '" placeholder="' + esc(ph || '') + '"' + (req ? ' required' : '') + '>' + (hint ? '<span class="hint">' + hint + '</span>' : '') + '</div>'; }
  function s(id, label, opts, req) { return '<div class="f"><label for="' + id + '">' + label + (req ? ' *' : '') + '</label><select id="' + id + '" name="' + id + '"' + (req ? ' required' : '') + '><option value="">Choisir…</option>' + opts.map(function (o) { return '<option>' + esc(o) + '</option>'; }).join('') + '</select></div>'; }
  function two(a, b) { return '<div class="two">' + a + b + '</div>'; }
  function openForm(mode, club) {
    var c = club && DATA.clubs.filter(function (x) { return x.id === club; })[0];
    var title = mode === 'add' ? 'Ajouter un club' : 'Corriger une info';
    var body;
    if (mode === 'add') {
      body = '<p class="hint" style="margin:0">Un champ par info : remplis ce que tu connais, seuls les champs avec * sont obligatoires.</p>' +
        '<p class="sec">Le club</p>' + f('Nom complet', 'Nom complet du club', 'text', 'Ex. : Athlétique Club de Saint-Paul', 1) + f('Nom usuel', 'Nom usuel ou sigle', 'text', 'Ex. : AC Saint-Paul') +
        two(s('Type', 'Type de club', TYPES, 1), s('FFA', 'Affilié à la FFA ?', ['Oui', 'Non', 'Je ne sais pas'])) +
        f('Courses organisées', 'Courses organisées par le club', 'text', 'Ex. : Trail des Goyaviers, Boucle du Piton', 0, 'Sépare-les par une virgule.') +
        '<p class="sec">Où le trouver</p>' + two(s('Commune', 'Commune', Object.keys(CO).sort(function (a, b) { return a.localeCompare(b, 'fr'); }), 1), f('Quartier', 'Quartier ou lieu-dit', 'text', 'Ex. : La Chaloupe')) +
        f('Adresse', 'Adresse du club', 'text', 'Ex. : 12 rue des Lilas, 97460 Saint-Paul') + f('Entraînement', 'Lieu d’entraînement', 'text', 'Ex. : Stade Paul Julius Bénard') +
        '<p class="sec">Le contacter</p>' + two(f('E-mail club', 'E-mail du club', 'email', 'club@exemple.re'), f('Téléphone club', 'Téléphone du club', 'tel', '0692 00 00 00')) +
        '<p class="sec">En ligne</p>' + f('Site', 'Site internet', 'url', 'https://') + two(f('Facebook', 'Page Facebook', 'url', 'https://facebook.com/…'), f('Instagram', 'Instagram', 'url', 'https://instagram.com/…')) +
        f('Autre réseau', 'Autre réseau (Strava, WhatsApp, TikTok…)', 'url', 'https://') +
        f('Logo', 'Lien vers le logo', 'url', 'https://…', 0, 'Le lien d’une image du logo (ou envoie-la à contact@dossardpei.re).') +
        '<p class="sec">Toi</p>' + two(s('Expéditeur', 'Tu es…', ['Membre ou dirigeant du club', 'Coureur, ami du club', 'Autre']), f('email', 'Ton e-mail (pour te répondre)', 'email', 'prenom@exemple.re'));
    } else {
      body = '<div class="f"><label for="Club">Club</label><input id="Club" name="Club" type="text" value="' + esc(c ? c.nom : '') + '"></div>' +
        '<div class="f"><label for="Correction">Qu’est-ce qui est faux ou manquant ? *</label><textarea id="Correction" name="Correction" rows="4" required placeholder="Ex. : nouvelle adresse, autre numéro, logo à changer…"></textarea></div>' +
        f('email', 'Ton e-mail (facultatif, pour te répondre)', 'email', 'prenom@exemple.re');
    }
    $('#formbox').innerHTML = '<form class="fform" id="theform" novalidate><div class="dhead"><h2 id="formtitle">' + title + '</h2><button type="button" class="x" data-close aria-label="Fermer">✕</button></div>' + body +
      '<input type="checkbox" name="botcheck" style="display:none" tabindex="-1" autocomplete="off"><p class="err" id="ferr" hidden></p><button type="submit" class="cta" style="align-self:flex-start">Envoyer</button></form>';
    var d = $('#dform'); d.dataset.mode = mode; d.dataset.club = c ? c.id : '';
    if ($('#dclub').open) $('#dclub').close();
    if (!d.open) d.showModal();
  }
  function sendForm(e) {
    e.preventDefault();
    var form = e.target, d = $('#dform'), err = $('#ferr');
    if (!form.checkValidity()) { err.hidden = false; err.textContent = 'Il manque un champ obligatoire, ou un e-mail / lien mal écrit.'; form.reportValidity(); return; }
    var fd = new FormData(form), o = {};
    fd.forEach(function (v, k) { if (v !== '' && k !== 'botcheck') o[k] = v; });
    if (fd.get('botcheck')) return;
    o.access_key = WEB3_KEY;
    o.subject = d.dataset.mode === 'add' ? 'Clubs péi : nouveau club – ' + (o['Nom complet'] || '') : 'Clubs péi : correction – ' + (o.Club || d.dataset.club);
    o.from_name = 'Clubs péi (dossardpei.re/clubs)';
    if (d.dataset.club) o['Fiche'] = 'https://dossardpei.re/clubs/#' + d.dataset.club;
    var btn = form.querySelector('[type=submit]'); btn.disabled = true; btn.textContent = 'Envoi…';
    fetch('https://api.web3forms.com/submit', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(o) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || j.success === false) throw new Error(); }); })
      .then(function () { $('#formbox').innerHTML = '<div class="done"><h2>Merci !</h2><p>C’est bien reçu. On vérifie et on met la fiche en ligne (ou à jour) sous quelques jours.</p><p style="margin-top:16px"><button type="button" class="cta" data-close>Fermer</button></p></div>'; })
      .catch(function () { btn.disabled = false; btn.textContent = 'Envoyer'; err.hidden = false; err.innerHTML = 'L’envoi n’a pas marché. Réessaie, ou écris-nous à <a href="mailto:contact@dossardpei.re">contact@dossardpei.re</a>.'; });
  }

  /* barre du haut : apparaît quand le grand logo sort de l'écran (comme l'accueil) */
  function topbar() {
    var t = $('#topbar'), big = $('#bigbrand'); if (!t || !big) return;
    var tick = false, f = function () { tick = false; var r = big.getBoundingClientRect(), d = Math.max(0, Math.min(1, scrollY / Math.max(80, r.bottom + scrollY - 40))); t.style.setProperty('--hp', d.toFixed(3)); t.classList.toggle('on', r.bottom < 0); };
    addEventListener('scroll', function () { if (!tick) { tick = true; requestAnimationFrame(f); } }, { passive: true }); f();
  }

  /* ---------- événements ---------- */
  function bind() {
    var t; $('#q').addEventListener('input', function (e) { clearTimeout(t); t = setTimeout(function () { st.q = e.target.value; render(); }, 120); });
    $('#openf').addEventListener('click', function () { syncFilters(); $('#dfilters').showModal(); });
    $('#dfilters').addEventListener('click', function (e) {
      var b = e.target.closest('[data-k]'); if (b) { var k = b.dataset.k; st[k] = st[k] === b.dataset.v ? '' : b.dataset.v; syncFilters(); render(); }
    });
    $('#fcommune').addEventListener('change', function (e) { st.commune = e.target.value; render(); });
    $('#fffa').addEventListener('change', function (e) { st.ffa = e.target.value; render(); });
    $('#fclear').addEventListener('click', function () { st.sect = st.type = st.commune = st.ffa = ''; syncFilters(); render(); });
    $('#near').addEventListener('click', function () {
      if (st.near) { st.near = null; render(); return; }
      if (!navigator.geolocation) return;
      var b = $('#near'); b.disabled = true;
      navigator.geolocation.getCurrentPosition(function (p) { b.disabled = false; st.near = [p.coords.latitude, p.coords.longitude]; render(); scrollTo({ top: $('#main').offsetTop - 8, behavior: 'smooth' }); },
        function () { b.disabled = false; alert('Position indisponible. Choisis plutôt ta commune dans Filtres.'); }, { timeout: 10000, maximumAge: 600000 });
    });
    document.addEventListener('click', function (e) {
      var c = e.target.closest('[data-clear]'); if (c) { if (c.dataset.clear === 'commune') st.commune = ''; else { st = { q: '', sect: '', type: '', commune: '', ffa: '', near: null }; $('#q').value = ''; } render(); }
      var fx = e.target.closest('[data-fix]'); if (fx) { e.preventDefault(); openForm('fix', fx.dataset.fix); }
      var cl = e.target.closest('[data-close]'); if (cl) { var dl = cl.closest('dialog'); if (dl) closeDlg(dl); }
      var gb = e.target.closest('.go-b[aria-haspopup]'); document.querySelectorAll('.go-m:not([hidden])').forEach(function (m) { if (!gb || m !== gb.nextElementSibling) { m.hidden = true; m.previousElementSibling.setAttribute('aria-expanded', 'false'); } });
      if (gb) { var mm = gb.nextElementSibling; mm.hidden = !mm.hidden; gb.setAttribute('aria-expanded', String(!mm.hidden)); }
    });
    $('#openadd').addEventListener('click', function () { openForm('add'); });
    $('#formbox').addEventListener('submit', sendForm);
    $('#dclub').addEventListener('close', function () { document.title = 'Clubs péi : les clubs de course et de trail de La Réunion – Dossard Péi'; if (location.hash && location.hash !== '#ajouter') history.replaceState(null, '', location.pathname + location.search); });
    [$('#dclub'), $('#dform'), $('#dfilters')].forEach(function (d) { d.addEventListener('click', function (e) { if (e.target === d) closeDlg(d); }); d.addEventListener('cancel', function (e) { e.preventDefault(); closeDlg(d); }); });
    window.addEventListener('hashchange', onHash);
  }

  fetch('clubs.json?v=1').then(function (r) { return r.json(); }).then(function (j) {
    DATA = j; POS = j.sprite.pos;
    fillCommunes(); bind(); render(); topbar();
    if (location.hash === '#ajouter') openForm('add'); else onHash();
  }).catch(function () { $('#list').innerHTML = '<p class="empty">Impossible de charger les clubs. Recharge la page.</p>'; });
})();
