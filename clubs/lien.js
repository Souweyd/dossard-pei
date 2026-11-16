/* Clubs péi : sur la fiche d'une course, lien « Fiche du club » vers l'organisateur (dossardpei.re/clubs/<id>/).
   Autonome : lit /clubs/liens.json (fait par tools/gen_clubs.py) et complète la ligne « Organisateur : … »
   de la fiche ouverte. Si la fiche change de forme, rien ne s'affiche et rien ne casse. */
(function () {
  if (window.__dpClubs) return; window.__dpClubs = 1;
  var L = null, busy = false;
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function rid() { var m = location.pathname.match(/^\/course\/([a-z0-9-]+)\/?$/); return m ? m[1] : ''; }
  function apply() {
    busy = false;
    var id = rid(); if (!id || !L) return;
    var cs = L.courses[id]; if (!cs || !cs.length) return;
    var ns = document.querySelectorAll('.dlg .links .note');
    for (var i = 0; i < ns.length; i++) {
      var n = ns[i];
      if (n.dataset.club === id || !/^Organisateur/.test(n.textContent)) continue;
      var old = n.parentNode.querySelector('.dpclub'); if (old) old.remove();
      n.dataset.club = id;
      var a = document.createElement('span'); a.className = 'note dpclub';
      a.innerHTML = cs.map(function (c) { return '<a href="/clubs/' + esc(c) + '/" data-goatcounter-click="club/' + esc(c) + '">Fiche du club ' + esc(L.noms[c] || c) + ' ›</a>'; }).join(' · ');
      n.insertAdjacentElement('afterend', a);
    }
  }
  function go() { if (!busy) { busy = true; requestAnimationFrame(apply); } }
  fetch('/clubs/liens.json').then(function (r) { return r.json(); }).then(function (j) {
    L = j; go();
    new MutationObserver(go).observe(document.body, { childList: true, subtree: true });
    addEventListener('popstate', go);
  }).catch(function () {});
})();
