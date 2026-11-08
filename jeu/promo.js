/* Entrées du site vers le jeu « Une histoire de dossard ».
   Autonome : ajoute la pastille « Le jeu » à côté de chaque bouton Calendrier 2027, une carte dans le Scroll
   (juste après la première course, pour ne pas gêner le saut automatique vers la première course quand on
   filtre), et un lien en pied de page. Liens dans le même onglet, avec ?ref= pour GoatCounter.
   Ne touche à rien d'autre : si un élément du site change de nom, l'entrée correspondante ne s'affiche pas. */
(function () {
  if (window.__dpJeu) return; window.__dpJeu = 1;
  var URL = '/jeu/';
  var CSS = '.dpjeu-pill{display:inline-flex!important;align-items:center;gap:6px;margin:6px 0 0 8px;background:#ffd400!important;color:#1d2523!important;border:0!important;text-decoration:none!important;white-space:nowrap;vertical-align:middle;width:auto!important;max-width:none!important}'
    + '.dpjeu-pill svg{width:18px!important;height:18px!important;min-width:0!important;flex:none;margin:0!important}'
    + '.dpjeu-new{background:#c62828;color:#fff;font-size:.68em;font-weight:700;padding:2px 7px;border-radius:99px;line-height:1.4}'
    + '.dpjeu-card .rcard .pimg{object-fit:cover}'
    + '.dpjeu-card .rst{background:#ffd400!important;color:#1d2523!important}'
    + '.dpjeu-card .rmore .dpjeu-go{flex:1;display:flex;align-items:center;justify-content:center;background:#ffd400;color:#1d2523;text-decoration:none;font-weight:800}'
    + '@media (max-width:360px){.dpjeu-pill{margin-left:0;margin-top:8px}}';
  var BIB = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5" fill="#fff" stroke="#1d2523" stroke-width="2"/><path d="M4.2 6.2h15.6v3.3H4.2z" fill="#1d4f9c"/><path d="M4 9.5h16" stroke="#1d2523" stroke-width="2"/><circle cx="6.5" cy="12.5" r="1" fill="#1d2523"/><circle cx="17.5" cy="12.5" r="1" fill="#1d2523"/></svg>';

  function style() {
    if (document.getElementById('dpjeu-css')) return;
    var s = document.createElement('style'); s.id = 'dpjeu-css'; s.textContent = CSS; document.head.appendChild(s);
  }
  function pills() {
    var bs = document.querySelectorAll('.qsaison');
    for (var i = 0; i < bs.length; i++) {
      var b = bs[i];
      if (b.nextElementSibling && b.nextElementSibling.classList.contains('dpjeu-pill')) continue;
      var a = document.createElement('a');
      a.className = 'dpjeu-pill';
      var cs = getComputedStyle(b);
      a.style.cssText = 'padding:' + cs.padding + ';border-radius:' + cs.borderRadius + ';font:' + cs.font + ';box-shadow:' + cs.boxShadow + ';line-height:' + cs.lineHeight;
      a.href = URL + '?ref=' + (b.closest('.rhome') ? 'accueil' : 'liste');
      a.innerHTML = BIB + 'Le jeu <span class="dpjeu-new">Nouveau</span>';
      b.insertAdjacentElement('afterend', a);
    }
  }
  function card() {
    var feed = document.querySelector('.rfeed');
    if (!feed) return;
    var first = feed.querySelector('.rs[data-id]'), have = feed.querySelector('.dpjeu-card');
    if (!first) { if (have) have.remove(); return; }
    if (have && have.previousElementSibling === first) return;
    if (have) have.remove();
    var s = document.createElement('section');
    s.className = 'rs rs2 dpjeu-card';
    s.innerHTML = '<div class="bgb" style="background-image:url(\'' + URL + 'affiche.jpg\')"></div>'
      + '<div class="rcard"><img class="pimg" src="' + URL + 'affiche.jpg" alt="Affiche du jeu Une histoire de dossard" loading="lazy" decoding="async"><span class="rst">Nouveau</span></div>'
      + '<div class="shdt"></div><div class="shd"></div>'
      + '<div class="rinfo"><div class="rm">Gratuit · sur ton téléphone</div><h2>Une histoire de dossard</h2>'
      + '<div class="rpills"><span style="--dc:var(--c-trail)"><i></i>Le jeu de trail de Dossard Péi</span><span>6 courses</span><span>2 coureurs</span></div></div>'
      + '<div class="rmore"><a class="rv dpjeu-go" href="' + URL + '?ref=scroll">Jouer</a></div>';
    first.insertAdjacentElement('afterend', s);
  }
  function foot() {
    var rows = document.querySelectorAll('.sitefoot .legrow');
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].querySelector('.dpjeu-foot')) continue;
      rows[i].insertAdjacentHTML('afterbegin', '<a class="dpjeu-foot" href="' + URL + '?ref=pied">Le jeu : Une histoire de dossard</a> · ');
    }
  }
  var busy = false;
  function run() {
    if (busy) return; busy = true;
    try { style(); pills(); card(); foot(); } catch (e) {}
    busy = false;
  }
  var t;
  function later() { clearTimeout(t); t = setTimeout(run, 60); }
  function start() {
    run();
    new MutationObserver(later).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
