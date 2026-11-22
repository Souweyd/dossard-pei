/* Clubs péi — annuaire des clubs (dossardpei.re/clubs/) */
(function () {
  'use strict';
  var WEB3_KEY = '2b5c040f-3abd-4227-b2db-786027df41b1';
  var SPRITE = '/clubs/logos.webp?v=1';
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
  var DATA = null, POS = {}, LIENS = { courses: {}, clubs: {} }, ROUTING = false;
  var st = { q: '', sect: '', type: '', commune: '', ffa: '', jeunes: '', near: null };

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
      if (st.jeunes && !(c.jeunes && c.jeunes.length)) return false;
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
      '<div class="body"><h3><a href="/clubs/' + esc(c.id) + '/" data-club="' + esc(c.id) + '">' + esc(c.nom) + '</a></h3>' +
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
    var nf = (st.sect ? 1 : 0) + (st.type ? 1 : 0) + (st.commune ? 1 : 0) + (st.ffa !== '' ? 1 : 0) + (st.jeunes ? 1 : 0);
    var b = $('#f-count'); b.hidden = !nf; b.textContent = nf;
    var s = '<span class="pill">' + list.length + (list.length > 1 ? ' clubs' : ' club') + '</span>';
    if (st.commune) s += '<button type="button" class="pill" data-clear="commune">' + esc(st.commune) + ' <span aria-hidden="true">✕</span><span class="sr">Retirer ce filtre</span></button>';
    if (nf || st.q || st.near) s += '<button type="button" class="clear" data-clear="all">✕ Effacer les filtres</button>';
    $('#state').innerHTML = s;
    $('#fshow').textContent = 'Voir ' + list.length + (list.length > 1 ? ' clubs' : ' club');
    $('#near').setAttribute('aria-pressed', st.near ? 'true' : 'false');
    if (view === 'carte') drawMap();
  }

  /* ---------- filtres ---------- */
  function chipsFor(el, vals, key) {
    el.innerHTML = vals.map(function (v) { return '<button type="button" class="chip" aria-pressed="' + (st[key] === v) + '" data-k="' + key + '" data-v="' + esc(v) + '">' + (key === 'type' ? '<i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:' + COL[v] + '"></i>' : '') + esc(v) + '</button>'; }).join('');
  }
  function syncFilters() {
    chipsFor($('#fsect'), SECTS, 'sect'); chipsFor($('#ftype'), TYPES, 'type');
    $('#fcommune').value = st.commune; $('#fffa').value = st.ffa; $('#fjeunes').value = st.jeunes;
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
    function svg(p, cl) { return '<svg class="' + (cl || 'i') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>'; }
    var P = {
      tel: '<path d="M6.6 3.5h2.6l1.5 4-2 1.3a11 11 0 0 0 6.5 6.5l1.3-2 4 1.5v2.6c0 1.1-.9 2-2 2A16.5 16.5 0 0 1 4.6 5.5c0-1.1.9-2 2-2z"/>',
      mail: '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6.5L20.5 7"/>',
      pin: '<path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.6"/>',
      web: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.7 5.6 3.7 9s-1.2 6.4-3.7 9c-2.5-2.6-3.7-5.6-3.7-9S9.5 5.6 12 3z"/>',
      shr: '<path d="M12 15V3.5M7.5 8 12 3.5 16.5 8"/><path d="M5 12.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-6.5"/>',
      chev: '<path d="M9 6l6 6-6 6"/>'
    };
    function itin(q) { var e = encodeURIComponent(q), m = [['Google Maps', 'https://www.google.com/maps/dir/?api=1&destination=' + e], ['Waze', 'https://waze.com/ul?q=' + e + '&navigate=yes']]; if (IOS) m.unshift(['Plans (Apple)', 'https://maps.apple.com/?daddr=' + e]); return m; }
    var tel1 = c.tel ? String(c.tel).split('/')[0].trim() : '';
    var dest = c.adresse ? c.adresse + ', La Réunion' : c.entrainement ? c.entrainement + ', ' + baseCommune(c.commune) + ', La Réunion' : '';
    var host = function (u) { return u.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, ''); };
    // barre d'actions
    var bar = '';
    if (tel1) bar += '<a class="ab" href="' + telHref(tel1) + '">' + svg(P.tel) + 'Appeler</a>';
    if (c.mail) bar += '<a class="ab" href="mailto:' + esc(c.mail) + '">' + svg(P.mail) + 'E-mail</a>';
    if (dest) bar += '<div class="go abw"><button type="button" class="go-b ab" aria-haspopup="true" aria-expanded="false">' + svg(P.pin) + 'Itinéraire</button><div class="go-m" hidden>' + itin(dest).map(function (m) { return '<a href="' + m[1] + '" target="_blank" rel="noopener">' + m[0] + '</a>'; }).join('') + '</div></div>';
    if (c.site) bar += '<a class="ab" href="' + esc(c.site) + '" target="_blank" rel="noopener">' + svg(P.web) + 'Site</a>';
    bar += '<button type="button" class="ab" data-share="' + esc(c.id) + '">' + svg(P.shr) + 'Partager</button>';
    // coordonnées
    var dl = '';
    var NONE = '<span class="none" aria-label="non renseigné">–</span>';
    function row(l, v) { dl += '<dt>' + l + '</dt><dd>' + (v || NONE) + '</dd>'; }
    row('Adresse', c.adresse && esc(c.adresse));
    row('Entraînement', c.entrainement && esc(c.entrainement));
    row('Téléphone', c.tel && String(c.tel).split('/').map(function (t) { t = t.trim(); return '<a href="' + telHref(t) + '">' + esc(t) + '</a>'; }).join(' / '));
    row('E-mail', c.mail && '<a href="mailto:' + esc(c.mail) + '">' + esc(c.mail) + '</a>');
    row(c.site && c.siteLabel && c.siteLabel !== 'Site' ? esc(c.siteLabel) : 'Site', c.site && '<a href="' + esc(c.site) + '" target="_blank" rel="noopener">' + esc(host(c.site)) + '</a>');
    row('Réseaux', c.reseaux.length && '<span class="nets">' + c.reseaux.map(function (r) { var n = NET[r.t] || NET.web; return '<a class="net' + (n.b ? ' brand' : '') + '" href="' + esc(r.url) + '" target="_blank" rel="noopener" aria-label="' + esc(n.l) + '" title="' + esc(n.l) + '">' + n.s + '</a>'; }).join('') + '</span>');
    var JL = { u7: 'Moins de 7 ans', u11: '7 à 10 ans', u15: '11 à 14 ans' };
    // courses
    var lk = LIENS.clubs[c.id], M = ['JANV', 'FÉVR', 'MARS', 'AVR', 'MAI', 'JUIN', 'JUIL', 'AOÛT', 'SEPT', 'OCT', 'NOV', 'DÉC'];
    var rc = lk ? lk.r.map(function (r) { var p = r[2].split('-'); return '<a class="rc" href="/course/' + esc(r[0]) + '/"><span class="dt"><b>' + (+p[2]) + '</b><small>' + M[+p[1] - 1] + '</small></span><span class="n">' + esc(r[1]) + '</span>' + svg(P.chev) + '</a>'; }).join('') : '';
    var oth = lk ? lk.autres : c.courses;
    var courses = '<div class="sec"><h3>Courses organisées</h3>' + (rc || oth.length ? rc + (oth.length ? '<p class="oth">' + (rc ? 'Aussi : ' : '') + oth.map(esc).join(', ') + '</p>' : '') : '<p class="oth">' + NONE + '</p>') + '</div>';
    $('#club').innerHTML = '<div class="fiche fa" style="--c:' + COL[c.type] + ';position:relative">' +
      banner(c) +
      '<div class="top">' + medal(c, 80) + '</div>' +
      '<div class="id"><h2>' + esc(c.nom) + '</h2>' + (c.complet ? '<p class="sub">' + esc(c.complet) + '</p>' : '') +
      '<div class="chips"><span>' + esc(c.type) + '</span><span>' + esc(c.commune) + '</span>' + (c.ffa ? '<span>Affilié FFA</span>' : '') + '</div></div>' +
      '<div class="bar">' + bar + '</div>' +
      '<div class="sec"><h3>Coordonnées</h3><dl>' + dl + '</dl></div>' +
      '<div class="sec"><h3>Section jeunes' + (c.jeunes && c.jeunes.length ? ' <span>· annuaire FFA</span>' : '') + '</h3>' + (c.jeunes && c.jeunes.length ? '<div class="kids">' + c.jeunes.map(function (k) { return '<span>' + JL[k] + '</span>'; }).join('') + '</div>' : '<p class="oth">' + NONE + '</p>') + '</div>' +
      courses +
      '<p class="foot"><button type="button" class="lnk" data-maj="' + esc(c.id) + '">Mettre à jour la fiche</button></p></div>';
    $('#fbt').textContent = c.nom; $('#dclub .fbar').style.setProperty('--tp', '0');
    var d = $('#dclub'); if (!d.open) d.showModal(); $('#club').scrollTop = 0; fiche(); fades($('#club'));
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
  /* fondu en haut / en bas de ce qui défile, et barre de titre de la fiche (comme les fiches courses) */
  function fades(s) { if (!s) return; var top = s.scrollTop, rest = s.scrollHeight - s.clientHeight - top; var d = s.parentElement; d.style.setProperty('--ft', (s.id === 'club' ? 0 : Math.min(24, Math.max(0, top))) + 'px'); d.style.setProperty('--fb', Math.min(28, Math.max(0, rest)) + 'px'); }
  function fiche() { var s = $('#club'), h = s.querySelector('h2'), bar = $('#dclub .fbar'); if (!h || !h.offsetHeight || s.scrollTop <= 0) { bar.style.setProperty('--tp', '0'); return; } var tp = Math.max(0, Math.min(1, (s.scrollTop - (h.offsetTop + h.offsetHeight - 56)) / 24)); bar.style.setProperty('--tp', tp.toFixed(2)); }
  /* glisser vers le bas pour fermer (tiroir sur mobile), comme les fiches courses */
  function sheetSwipe(d) {
    var y0 = null, dy = 0, sc = function () { return d.lastElementChild; };
    d.addEventListener('touchstart', function (e) { var s = sc(); y0 = matchMedia('(max-width: 640px)').matches && (!s || s.scrollTop <= 0) && !e.target.closest('input,textarea,select') ? e.touches[0].clientY : null; dy = 0; }, { passive: true });
    d.addEventListener('touchmove', function (e) { if (y0 == null) return; var s = sc(); dy = e.touches[0].clientY - y0; if (dy > 0 && (!s || s.scrollTop <= 0)) { d.style.transition = 'none'; d.style.transform = 'translateY(' + dy + 'px)'; } }, { passive: true });
    d.addEventListener('touchend', function () {
      if (y0 == null) return; y0 = null; d.style.transition = '';
      if (dy > 110) { d.style.transform = 'translateY(100%)'; d.style.transition = 'transform .22s ease-in'; closeDlg(d); setTimeout(function () { d.style.transform = ''; d.style.transition = ''; }, 260); }
      else d.style.transform = '';
    });
  }
  function pathId() { var m = location.pathname.match(/^\/clubs\/([a-z0-9-]+)\/?$/); return m ? m[1] : ''; }
  function go(id) { var u = id ? '/clubs/' + id + '/' : '/clubs/'; if (location.pathname !== u) history.pushState(null, '', u); }
  function route() { var id = pathId(); ROUTING = true; if (id && DATA.clubs.some(function (x) { return x.id === id; })) openClub(id); else closeClub(); ROUTING = false; }
  function onHash() { var id = decodeURIComponent(location.hash.slice(1)); if (id === 'ajouter') return; if (id && DATA.clubs.some(function (x) { return x.id === id; })) { history.replaceState(null, '', '/clubs/' + id + '/'); route(); } }
  function dateFr(s) { var p = s.split('-'); return +p[2] + ' ' + ['janv.', 'févr.', 'mars', 'avril', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'][+p[1] - 1] + ' ' + p[0]; }
  function share(id) {
    var c = DATA.clubs.filter(function (x) { return x.id === id; })[0], url = 'https://dossardpei.re/clubs/' + id + '/';
    if (navigator.share) { navigator.share({ title: c.nom + ' – Clubs péi', text: c.nom + ' – ' + c.type + ' · ' + c.commune, url: url }).catch(function () {}); return; }
    var done = function () { toast('Lien de la fiche copié'); };
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { prompt('Lien de la fiche :', url); }); else prompt('Lien de la fiche :', url);
  }
  function toast(t) { var e = document.createElement('div'); e.className = 'toast'; e.setAttribute('role', 'status'); e.textContent = t; (document.querySelector('dialog[open]') || document.body).appendChild(e); setTimeout(function () { e.classList.add('out'); }, 1800); setTimeout(function () { e.remove(); }, 2200); }

  /* ---------- formulaires ---------- */
  var PRE = null;
  function pv(id) { return PRE && PRE[id] != null ? PRE[id] : ''; }
  function f(id, label, type, ph, req, hint) { return '<div class="f"><label for="' + id + '">' + label + (req ? ' *' : '') + '</label><input id="' + id + '" name="' + id + '" type="' + (type || 'text') + '" placeholder="' + esc(ph || '') + '"' + (req ? ' required' : '') + (pv(id) ? ' value="' + esc(pv(id)) + '"' : '') + ' data-init="' + esc(pv(id)) + '">' + (hint ? '<span class="hint">' + hint + '</span>' : '') + '</div>'; }
  function s(id, label, opts, req) { return '<div class="f"><label for="' + id + '">' + label + (req ? ' *' : '') + '</label><select id="' + id + '" name="' + id + '"' + (req ? ' required' : '') + '><option value="">Choisir…</option>' + opts.map(function (o) { return '<option' + (pv(id) === o ? ' selected' : '') + '>' + esc(o) + '</option>'; }).join('') + '</select></div>'; }
  function two(a, b) { return '<div class="two">' + a + b + '</div>'; }
  function openForm(mode, club) {
    var c = club && DATA.clubs.filter(function (x) { return x.id === club; })[0];
    var title = mode === 'add' ? 'Ajouter un club' : mode === 'maj' ? 'Mettre à jour la fiche' : 'Corriger une info';
    var body;
    PRE = null;
    if (mode === 'maj' && c) {
      var rz = function (t) { var x = c.reseaux.filter(function (r) { return r.t === t; })[0]; return x ? x.url : ''; }, other = c.reseaux.filter(function (r) { return r.t !== 'fb' && r.t !== 'ig'; })[0], q = c.commune.match(/\((.*)\)/);
      PRE = { 'Nom complet': c.complet || c.nom, 'Nom usuel': c.nom, 'Type': c.type, 'FFA': c.ffa ? 'Oui' : 'Non', 'Courses organisées': c.courses.join(', '), 'Commune': baseCommune(c.commune), 'Quartier': q ? q[1] : '', 'Adresse': c.adresse, 'Entraînement': c.entrainement, 'E-mail club': c.mail, 'Téléphone club': c.tel, 'Site': c.site, 'Facebook': rz('fb'), 'Instagram': rz('ig'), 'Autre réseau': other ? other.url : ''};
    }
    if (mode === 'add' || mode === 'maj') {
      body = '<p class="hint" style="margin:0">' + (mode === 'maj' ? 'La fiche actuelle est déjà remplie : change ce qui doit l’être et ajoute ce qui manque (horaires d’entraînement, section jeunes, logo…).' : 'Un champ par info : remplis ce que tu connais, seuls les champs avec * sont obligatoires.') + '</p>' +
        '<p class="sec">Le club</p>' + f('Nom complet', 'Nom complet du club', 'text', 'Ex. : Athlétique Club de Saint-Paul', 1) + f('Nom usuel', 'Nom usuel ou sigle', 'text', 'Ex. : AC Saint-Paul') +
        two(s('Type', 'Type de club', TYPES, 1), s('FFA', 'Affilié à la FFA ?', ['Oui', 'Non', 'Je ne sais pas'])) +
        f('Courses organisées', 'Courses organisées par le club', 'text', 'Ex. : Trail des Goyaviers, Boucle du Piton', 0, 'Sépare-les par une virgule.') +
        '<p class="sec">Où le trouver</p>' + two(s('Commune', 'Commune', Object.keys(CO).sort(function (a, b) { return a.localeCompare(b, 'fr'); }), 1), f('Quartier', 'Quartier ou lieu-dit', 'text', 'Ex. : La Chaloupe')) +
        f('Adresse', 'Adresse du club', 'text', 'Ex. : 12 rue des Lilas, 97460 Saint-Paul') + f('Entraînement', 'Lieu d’entraînement', 'text', 'Ex. : Stade Paul Julius Bénard') +
        '<p class="sec">Le contacter</p>' + two(f('E-mail club', 'E-mail du club', 'email', 'club@exemple.re'), f('Téléphone club', 'Téléphone du club', 'tel', '0692 00 00 00')) +
        '<p class="sec">En ligne</p>' + f('Site', 'Site internet', 'url', 'https://') + two(f('Facebook', 'Page Facebook', 'url', 'https://facebook.com/…'), f('Instagram', 'Instagram', 'url', 'https://instagram.com/…')) +
        f('Autre réseau', 'Autre réseau (Strava, WhatsApp, TikTok…)', 'url', 'https://') +
        f('Logo', 'Lien vers le logo', 'url', 'https://…', 0, 'Le lien d’une image du logo (ou envoie-la à contact@dossardpei.re).') +
        (mode === 'maj' ? '<div class="f"><label for="Horaires">Jours et horaires d’entraînement</label><textarea id="Horaires" name="Horaires" rows="2" placeholder="Ex. : mardi et jeudi 18 h, dimanche 7 h en sortie trail" data-init=""></textarea></div><div class="f"><label for="Message">Autre chose à nous dire ?</label><textarea id="Message" name="Message" rows="2" data-init=""></textarea></div>' : '') +
        '<p class="sec">Toi</p>' + two(s('Expéditeur', 'Tu es…', ['Membre ou dirigeant du club', 'Coureur, ami du club', 'Autre']), f('email', 'Ton e-mail (pour te répondre)', 'email', 'prenom@exemple.re'));
    } else {
      body = '<div class="f"><label for="Club">Club</label><input id="Club" name="Club" type="text" value="' + esc(c ? c.nom : '') + '"></div>' +
        '<div class="f"><label for="Correction">Qu’est-ce qui est faux ou manquant ? *</label><textarea id="Correction" name="Correction" rows="4" required placeholder="Ex. : nouvelle adresse, autre numéro, logo à changer…"></textarea></div>' +
        f('email', 'Ton e-mail (facultatif, pour te répondre)', 'email', 'prenom@exemple.re');
    }
    $('#formbox').innerHTML = '<form class="fform" id="theform" novalidate><div class="dhead"><h2 id="formtitle">' + title + '</h2><button type="button" class="x" data-close aria-label="Fermer">×</button></div>' + body +
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
    if (d.dataset.mode === 'maj') { var ch = []; form.querySelectorAll('[data-init]').forEach(function (x) { if ((x.value || '') !== x.dataset.init) ch.push(x.name); }); o['Champs modifiés'] = ch.length ? ch.join(', ') : 'aucun'; }
    o.subject = d.dataset.mode === 'add' ? 'Clubs péi : nouveau club – ' + (o['Nom complet'] || '') : d.dataset.mode === 'maj' ? 'Clubs péi : mise à jour par le club – ' + (o['Nom usuel'] || d.dataset.club) : 'Clubs péi : correction – ' + (o.Club || d.dataset.club);
    o.from_name = 'Clubs péi (dossardpei.re/clubs)';
    if (d.dataset.club) o['Fiche'] = 'https://dossardpei.re/clubs/' + d.dataset.club + '/';
    var btn = form.querySelector('[type=submit]'); btn.disabled = true; btn.textContent = 'Envoi…';
    // 1. espace privé du site ; s'il ne répond pas, 2. envoi par e-mail (service de formulaires) comme avant
    var champs = {}; Object.keys(o).forEach(function (k) { if (['access_key', 'subject', 'from_name', 'email', 'Correction', 'Message', 'Fiche'].indexOf(k) < 0) champs[k] = String(o[k]); });
    var mine = { type: d.dataset.mode === 'add' ? 'club-ajout' : d.dataset.mode === 'maj' ? 'club-maj' : 'club-correction', sujet: o.subject, club: o['Nom complet'] || o['Nom usuel'] || o.Club || d.dataset.club || '',
      page: o.Fiche || '', email: o.email || '', message: o.Correction || o.Message || '', champs: champs };
    var ctl = window.AbortController ? new AbortController() : null; if (ctl) setTimeout(function () { ctl.abort(); }, 8000);
    fetch('/api/form', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(mine), signal: ctl ? ctl.signal : undefined })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || !j.ok) throw new Error(); }); })
      .catch(function () {
        return fetch('https://api.web3forms.com/submit', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(o) })
          .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || j.success === false) throw new Error(); }); });
      })
      .then(function () { $('#formbox').innerHTML = '<div class="done"><h2>Merci !</h2><p>C’est bien reçu. On vérifie et on met la fiche en ligne (ou à jour) sous quelques jours.</p><p style="margin-top:16px"><button type="button" class="cta" data-close>Fermer</button></p></div>'; })
      .catch(function () { btn.disabled = false; btn.textContent = 'Envoyer'; err.hidden = false; err.innerHTML = 'L’envoi n’a pas marché. Réessaie, ou écris-nous à <a href="mailto:contact@dossardpei.re">contact@dossardpei.re</a>.'; });
  }

  /* barre du haut + logo qui glisse jusqu'à la barre en défilant (repris de l'accueil) */
  function brandGhost(img) {
    var g = document.createElement('div'); g.className = 'bghost'; g.setAttribute('aria-hidden', 'true');
    g.style.cssText = 'display:flex;align-items:center;transform-origin:0 50%';
    var n = img.cloneNode(true); n.removeAttribute('id'); n.setAttribute('class', ''); n.style.cssText = 'width:' + img.getBoundingClientRect().width + 'px;height:auto;display:block;flex:none';
    g.appendChild(n); return g;
  }
  function topbar() {
    var big = $('#bigbrand'), t = $('#topbar'); if (!big || !t) return;
    var logo = big.querySelector('.biglogo'), busy = false, ghost = null;
    var reduced = function () { return matchMedia('(prefers-reduced-motion: reduce)').matches; };
    var f = function () {
      busy = false;
      if (reduced() || !logo) { var u = big.getBoundingClientRect().bottom < 0; t.classList.toggle('on', u); t.style.setProperty('--hp', u ? '1' : '0'); return; }
      logo.style.visibility = '';
      var r = logo.getBoundingClientRect(), L = { left: r.left, cy: r.top + r.height / 2 + scrollY, w: r.width }, c = { left: Math.max(16, (innerWidth - 1320) / 2), cy: 30, w: 36 };
      var d = Math.max(0, Math.min(1, scrollY / Math.max(80, L.cy - c.cy - 20)));
      t.style.setProperty('--hp', d.toFixed(3)); t.classList.toggle('on', d >= 1);
      if (d > 0 && d < 1) {
        if (!ghost) { ghost = brandGhost(logo); document.body.appendChild(ghost); }
        ghost.style.display = 'flex';
        var hgt = ghost.offsetHeight;
        ghost.style.left = L.left + 'px'; ghost.style.top = (L.cy - hgt / 2) + 'px';
        ghost.style.transform = 'translate(' + ((c.left - L.left) * d) + 'px,' + ((c.cy - L.cy) * d) + 'px) scale(' + (1 + (c.w / L.w - 1) * d) + ')';
        logo.style.visibility = 'hidden';
      } else { if (ghost) ghost.style.display = 'none'; logo.style.visibility = d >= 1 ? 'hidden' : ''; }
    };
    addEventListener('scroll', function () { if (!busy) { busy = true; requestAnimationFrame(f); } }, { passive: true });
    addEventListener('resize', f); requestAnimationFrame(f);
  }

  /* ---------- carte ---------- */
  var MAPB = [55.205, 55.845, -21.405, -20.855], MW = 1100, MH = 1013, COMMUNES = null, view = 'liste', selCom = '', VB = [0, 0, MW, MH], BASE = false;
  function proj(ll) { return [(ll[1] - MAPB[0]) / (MAPB[1] - MAPB[0]) * MW, (MAPB[3] - ll[0]) / (MAPB[3] - MAPB[2]) * MH]; }
  function full() { return document.body.classList.contains('mapfull'); }
  function setVB(v) {
    var w = Math.max(MW / 6, Math.min(MW, v[2])), h = w * MH / MW;
    var x = Math.max(-w * 0.25, Math.min(MW - w * 0.75, v[0])), y = Math.max(-h * 0.25, Math.min(MH - h * 0.75, v[1]));
    if (w >= MW) { x = 0; y = 0; }
    VB = [x, y, w, h]; $('#cmap').setAttribute('viewBox', VB.map(function (n) { return n.toFixed(1); }).join(' '));
    $('#z-all').hidden = w >= MW; $('#cmap').classList.toggle('zoomed', w < MW);
    pins();
  }
  function zoomAt(f, cx, cy) { var w = VB[2] / f, h = w * MH / MW; if (cx == null) { cx = VB[0] + VB[2] / 2; cy = VB[1] + VB[3] / 2; } setVB([cx - (cx - VB[0]) / f, cy - (cy - VB[1]) / f, w, h]); }
  function toMap(px, py) { var r = $('#cmap').getBoundingClientRect(), s = Math.max(VB[2] / r.width, VB[3] / r.height), ox = (r.width * s - VB[2]) / 2, oy = (r.height * s - VB[3]) / 2; return [VB[0] - ox + (px - r.left) * s, VB[1] - oy + (py - r.top) * s]; }
  function base() {
    if (BASE && COMMUNES) return;
    var h = '<image href="/ocean_sm.webp" x="-400" y="-400" width="' + (MW + 800) + '" height="' + (MH + 800) + '" preserveAspectRatio="none"/><image href="/relief_sm.webp" x="0" y="0" width="' + MW + '" height="' + MH + '" preserveAspectRatio="none"/>';
    if (COMMUNES) h += '<g class="cbord">' + COMMUNES.map(function (k) { return '<path d="' + k.d + '"/>'; }).join('') + '</g>';
    $('#mbase').innerHTML = h; BASE = !!COMMUNES;
  }
  function byCommune() { var by = {}; filtered().forEach(function (c) { var b = baseCommune(c.commune); (by[b] = by[b] || []).push(c); }); return by; }
  function pins() {
    var svg = $('#cmap'), by = byCommune(), r = svg.getBoundingClientRect(), W = r.width || 900, z = MW / VB[2];
    var K = Math.min(2.4, Math.max(1, 900 / W)) / Math.pow(z, 0.85), small = W / z * 1.0 < 600 && z < 2.2;
    var h = '';
    Object.keys(by).sort(function (a, b) { return by[a].length - by[b].length; }).forEach(function (k) {
      var p = CO[k]; if (!p) return; var xy = proj(p), cs = by[k], n = cs.length, R = n > 9 ? 17 : n > 1 ? 15 : 12, sw = 4, g = R - sw / 2, P = 2 * Math.PI * g, off = 0, seg = '', cnt = {};
      cs.forEach(function (c) { cnt[c.type] = (cnt[c.type] || 0) + 1; });
      TYPES.forEach(function (ty) { if (!cnt[ty]) return; var l = P * cnt[ty] / n; seg += '<circle r="' + g + '" class="seg" stroke="' + COL[ty] + '" stroke-width="' + sw + '" stroke-dasharray="' + l + ' ' + (P - l) + '" stroke-dashoffset="' + (-off) + '" transform="rotate(-90)"/>'; off += l; });
      var east = xy[0] > 900;
      h += '<g class="pin' + (selCom === k ? ' on' : '') + '" transform="translate(' + xy[0].toFixed(1) + ',' + xy[1].toFixed(1) + ') scale(' + K.toFixed(3) + ')" tabindex="0" role="button" data-com="' + esc(k) + '" aria-label="' + esc(k + ' : ' + n + (n > 1 ? ' clubs' : ' club')) + '"><circle r="26" class="hit"/><circle r="' + R + '" class="core"/>' + seg + '<text class="n" font-size="' + (n > 9 ? 15 : 14) + '">' + n + '</text>' + (small && selCom !== k ? '' : '<text class="lbl" ' + (east ? 'x="0" y="' + (R + 18) + '" style="text-anchor:middle"' : 'x="' + (R + 6) + '"') + ' font-size="17">' + esc(k) + '</text>') + '</g>';
    });
    $('#mpins').innerHTML = h;
  }
  function drawMap() {
    base(); pins();
    var by = byCommune(), sel = selCom && by[selCom];
    $('#maphint').hidden = !!sel;
    $('#mapsel').innerHTML = sel ? '<section class="grp"><h2>' + esc(selCom) + ' <small>' + sel.length + (sel.length > 1 ? ' clubs' : ' club') + '</small></h2><div class="grid">' + sel.sort(function (a, b) { return a.nom.localeCompare(b.nom, 'fr'); }).map(card).join('') + '</div></section>' : '';
    var mp = $('#mpop');
    if (sel && full()) {
      mp.innerHTML = '<div class="mpop-h"><div><b>' + esc(selCom) + '</b> <span>' + sel.length + (sel.length > 1 ? ' clubs' : ' club') + '</span></div><button type="button" class="mpop-x" aria-label="Fermer">×</button></div><div class="mpop-l">' +
        sel.map(function (c) { return '<a class="mpop-i" style="--c:' + COL[c.type] + '" href="/clubs/' + esc(c.id) + '/" data-club="' + esc(c.id) + '">' + medal(c, 44) + '<span><span class="mpop-n">' + esc(c.nom) + '</span><span class="mpop-m">' + esc(c.type) + (c.ffa ? ' · FFA' : '') + '</span></span></a>'; }).join('') + '</div>';
      mp.hidden = false;
    } else mp.hidden = true;
  }
  function setFull(on) {
    document.body.classList.toggle('mapfull', on); $('#map-full').hidden = on; $('#map-fullx').hidden = !on;
    document.documentElement.classList.toggle('noscroll', on || !!document.querySelector('dialog[open]'));
    drawMap();
  }
  function nearestCom() { var best = '', bd = 1e9, seen = {}; filtered().forEach(function (c) { var b = baseCommune(c.commune); if (seen[b] || !CO[b]) return; seen[b] = 1; var dd = km(st.near, CO[b]); if (dd < bd) { bd = dd; best = b; } }); return best; }
  function showSel() { if (full()) return; var s = $('#mapsel'); setTimeout(function () { var y = s.getBoundingClientRect().top + scrollY - Math.max(72, innerHeight * 0.4); if (y > scrollY) scrollTo({ top: y, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); }, 50); }
  function syncTabs() {
    document.querySelectorAll('#tabbar [data-tab]').forEach(function (b) { if (b.dataset.tab === view) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
    var a = document.querySelector('#tabbar [aria-current="page"]'); if (a) $('#tbpill .tbcur').innerHTML = a.querySelector('svg').outerHTML + '<span class="tbl">' + a.textContent.trim() + '</span>';
  }
  function setView(v) {
    view = v; $('#v-liste').setAttribute('aria-pressed', v === 'liste'); $('#v-carte').setAttribute('aria-pressed', v === 'carte');
    $('#mapview').hidden = v !== 'carte'; $('#list').hidden = v === 'carte'; syncTabs();
    if (v !== 'carte' && full()) setFull(false);
    if (v === 'carte') { if (st.near && !selCom) selCom = nearestCom(); if (!COMMUNES) fetch('/clubs/communes.json?v=1').then(function (r) { return r.json(); }).then(function (d) { COMMUNES = d; drawMap(); }).catch(function () {}); requestAnimationFrame(drawMap); }
  }
  function mapGestures() {
    var svg = $('#cmap'), drag = null, moved = false, pinch = null;
    svg.addEventListener('pointerdown', function (e) { if (e.pointerType === 'touch' && VB[2] >= MW && !full()) return; drag = { x: e.clientX, y: e.clientY, vb: VB.slice(), id: e.pointerId }; moved = false; });
    addEventListener('pointermove', function (e) {
      if (!drag || pinch || e.pointerId !== drag.id) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (!moved && Math.abs(dx) + Math.abs(dy) < 6) return;
      moved = true; svg.classList.add('dragging');
      var r = svg.getBoundingClientRect(), s = Math.max(VB[2] / r.width, VB[3] / r.height);
      setVB([drag.vb[0] - dx * s, drag.vb[1] - dy * s, drag.vb[2], drag.vb[3]]);
    });
    addEventListener('pointerup', function () { if (drag && moved) { svg.dataset.dragged = '1'; setTimeout(function () { delete svg.dataset.dragged; }, 60); } drag = null; svg.classList.remove('dragging'); });
    svg.addEventListener('click', function (e) { if (svg.dataset.dragged) { e.stopPropagation(); e.preventDefault(); } }, true);
    svg.addEventListener('wheel', function (e) { if (!full() && !e.ctrlKey && !e.metaKey) return; e.preventDefault(); var m = toMap(e.clientX, e.clientY); zoomAt(e.deltaY < 0 ? 1.25 : 0.8, m[0], m[1]); }, { passive: false });
    svg.addEventListener('dblclick', function (e) { var m = toMap(e.clientX, e.clientY); zoomAt(2, m[0], m[1]); });
    svg.addEventListener('touchstart', function (e) { if (e.touches.length !== 2) { pinch = null; return; } var a = e.touches[0], b = e.touches[1]; drag = null; pinch = { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), m: toMap((a.clientX + b.clientX) / 2, (a.clientY + b.clientY) / 2), w: VB[2] }; }, { passive: true });
    svg.addEventListener('touchmove', function (e) {
      if (!pinch || e.touches.length !== 2) return; e.preventDefault();
      var a = e.touches[0], b = e.touches[1], d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), cx = (a.clientX + b.clientX) / 2, cy = (a.clientY + b.clientY) / 2;
      var w = Math.max(MW / 6, Math.min(MW, pinch.w * pinch.d / d)), h = w * MH / MW, r = svg.getBoundingClientRect();
      setVB([pinch.m[0] - (cx - r.left) / r.width * w, pinch.m[1] - (cy - r.top) / r.height * h, w, h]);
    }, { passive: false });
    svg.addEventListener('touchend', function (e) { if (e.touches.length < 2) pinch = null; });
    $('#z-in').addEventListener('click', function () { zoomAt(1.6); });
    $('#z-out').addEventListener('click', function () { zoomAt(1 / 1.6); });
    $('#z-all').addEventListener('click', function () { setVB([0, 0, MW, MH]); });
    $('#map-full').addEventListener('click', function () { setFull(true); });
    $('#map-fullx').addEventListener('click', function () { setFull(false); });
    $('#mpop').addEventListener('click', function (e) { if (e.target.closest('.mpop-x')) { selCom = ''; drawMap(); } });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && full() && !document.querySelector('dialog[open]')) setFull(false); });
  }
  function tabMenu() {
    var tb = $('#tabbar'), pill = $('#tbpill'), dim = $('#tbdim');
    var menu = function (on) { if (on === undefined) on = !tb.classList.contains('open'); tb.classList.toggle('open', on); dim.classList.toggle('on', on); pill.setAttribute('aria-expanded', on ? 'true' : 'false'); if (on) { var c = tb.querySelector('[aria-current="page"]'); if (c) c.focus({ preventScroll: true }); } };
    pill.addEventListener('click', function () { menu(); });
    dim.addEventListener('click', function () { menu(false); });
    tb.addEventListener('click', function (e) { var b = e.target.closest('[data-tab]'); if (!b) return; menu(false); if (b.dataset.tab !== view) { setView(b.dataset.tab); scrollTo({ top: $('#main').offsetTop - 70, behavior: 'auto' }); } });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && tb.classList.contains('open')) menu(false); });
    var last = scrollY, t;
    addEventListener('scroll', function () { if (tb.classList.contains('open')) return; var y = scrollY; if (y > last + 2 && y > 40) pill.classList.add('mini'); else if (y < last - 2) pill.classList.remove('mini'); last = y; clearTimeout(t); t = setTimeout(function () { pill.classList.remove('mini'); }, 700); }, { passive: true });
    syncTabs();
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
    $('#fjeunes').addEventListener('change', function (e) { st.jeunes = e.target.value; render(); });
    $('#fclear').addEventListener('click', function () { st.sect = st.type = st.commune = st.ffa = st.jeunes = ''; syncFilters(); render(); });
    $('#near').addEventListener('click', function () {
      if (st.near) { st.near = null; render(); return; }
      if (!navigator.geolocation) return;
      var b = $('#near'); b.disabled = true;
      navigator.geolocation.getCurrentPosition(function (p) { b.disabled = false; st.near = [p.coords.latitude, p.coords.longitude]; if (view === 'carte') { selCom = nearestCom(); render(); showSel(); } else { render(); scrollTo({ top: $('#main').offsetTop - 8, behavior: 'smooth' }); } },
        function () { b.disabled = false; alert('Position indisponible. Choisis plutôt ta commune dans Filtres.'); }, { timeout: 10000, maximumAge: 600000 });
    });
    document.addEventListener('click', function (e) {
      var c = e.target.closest('[data-clear]'); if (c) { if (c.dataset.clear === 'commune') st.commune = ''; else { st = { q: '', sect: '', type: '', commune: '', ffa: '', jeunes: '', near: null }; $('#q').value = ''; } render(); }
      var fx = e.target.closest('[data-fix]'); if (fx) { e.preventDefault(); openForm('fix', fx.dataset.fix); }
      var mj = e.target.closest('[data-maj]'); if (mj) { e.preventDefault(); openForm('maj', mj.dataset.maj); }
      var sh = e.target.closest('[data-share]'); if (sh) { e.preventDefault(); share(sh.dataset.share); }
      var ca = e.target.closest('a[data-club]'); if (ca && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) { e.preventDefault(); go(ca.dataset.club); openClub(ca.dataset.club); }
      var cl = e.target.closest('[data-close]'); if (cl) { var dl = cl.closest('dialog'); if (dl) closeDlg(dl); }
      var gb = e.target.closest('.go-b[aria-haspopup]'); document.querySelectorAll('.go-m:not([hidden])').forEach(function (m) { if (!gb || m !== gb.nextElementSibling) { m.hidden = true; m.previousElementSibling.setAttribute('aria-expanded', 'false'); } });
      if (gb) { var mm = gb.nextElementSibling; mm.hidden = !mm.hidden; gb.setAttribute('aria-expanded', String(!mm.hidden)); }
    });
    $('#openadd').addEventListener('click', function () { openForm('add'); });
    $('#v-liste').addEventListener('click', function () { setView('liste'); });
    $('#v-carte').addEventListener('click', function () { setView('carte'); });
    var pick = function (e) { var p = e.target.closest('.pin'); if (!p) return; selCom = selCom === p.dataset.com ? '' : p.dataset.com; drawMap(); if (selCom) showSel(); };
    $('#cmap').addEventListener('click', pick);
    $('#cmap').addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(e); } });
    $('#formbox').addEventListener('submit', sendForm);
    $('#dclub').addEventListener('close', function () { document.title = 'Clubs péi : les clubs de course et de trail de La Réunion – Dossard Péi'; if (!ROUTING && pathId()) go(''); });
    $('#club').addEventListener('scroll', fiche, { passive: true });
    [$('#dclub'), $('#dform'), $('#dfilters')].forEach(function (d) { sheetSwipe(d); d.lastElementChild.addEventListener('scroll', function (e) { fades(e.currentTarget); }, { passive: true }); d.addEventListener('click', function (e) { if (e.target === d) closeDlg(d); }); d.addEventListener('cancel', function (e) { e.preventDefault(); closeDlg(d); }); });
    window.addEventListener('hashchange', onHash);
    window.addEventListener('popstate', route);
  }

  fetch('/clubs/liens.json').then(function (r) { return r.json(); }).then(function (l) { LIENS = l; }).catch(function () {}).then(function () { return fetch('/clubs/clubs.json?v=2'); }).then(function (r) { return r.json(); }).then(function (j) {
    DATA = j; POS = j.sprite.pos;
    fillCommunes(); bind(); mapGestures(); tabMenu(); render(); topbar(); var mo = new MutationObserver(function () { document.documentElement.classList.toggle('noscroll', !!document.querySelector('dialog[open]') || full()); document.querySelectorAll('dialog[open]').forEach(function (d) { setTimeout(function () { fades(d.lastElementChild); }, 30); }); }); document.querySelectorAll('dialog').forEach(function (d) { mo.observe(d, { attributes: true, attributeFilter: ['open'] }); }); var rz; addEventListener('resize', function () { clearTimeout(rz); rz = setTimeout(function () { if (view === 'carte') drawMap(); }, 200); });
    if (location.hash === '#ajouter') openForm('add'); else if (location.hash.length > 1) onHash(); else if (pathId()) route();
  }).catch(function () { $('#list').innerHTML = '<p class="empty">Impossible de charger les clubs. Recharge la page.</p>'; });
})();
