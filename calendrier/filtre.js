// /calendrier/<page>/ : opens the site with the page's filter (read by the app from the address)
(function () {
  try {
    var m = location.pathname.match(/^\/calendrier\/([a-z0-9-]+)\/?$/);
    if (!m || location.search) return;
    var s = m[1], q = "", M = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12};
    if (s === "ce-week-end") q = "quand=we";
    else if (/^(trail|route|cross)$/.test(s)) q = "type=" + s;
    else { var x = s.match(/^([a-z]+)-(\d{4})$/); if (x && M[x[1]]) q = "mois=" + x[2] + "-" + ("0" + M[x[1]]).slice(-2); }
    if (q) history.replaceState(history.state, "", location.pathname + "?" + q + location.hash);
  } catch (e) {}
})();
