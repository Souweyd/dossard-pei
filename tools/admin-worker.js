// Dossard Péi — service de la page admin (Cloudflare Worker, routes dossardpei.re/admin/api/* et dossardpei.re/api/form).
//
// /api/form (public) : reçoit les formulaires du site (contact, clubs) et les range dans l'espace MSG,
// lu seulement par l'admin. Effacés automatiquement au bout d'un an. Si ce service ne répond pas, le site
// envoie le message par e-mail comme avant.
//
// Accès : mot de passe choisi par le propriétaire (secret ADMIN_PASSWORD, 12 caractères minimum). Une fois
// entré, un cookie signé garde la session 30 jours sur l'appareil ; changer le mot de passe déconnecte tout le
// monde. 5 erreurs en 1 heure depuis un même appareil bloquent les essais pendant 1 heure.
// (Cloudflare Access reste accepté si ACCESS_TEAM et ACCESS_AUD sont renseignés.)
// Le service lit et écrit les fichiers de données du dépôt GitHub en un seul commit, et relaie les
// statistiques (compteur d'audience, Web Analytics). Aucune clé n'est dans ce fichier : elles sont
// des « secrets » du Worker, saisis par le propriétaire dans Cloudflare.
//
// Variables (Paramètres › Variables et secrets) :
//   REPO           Souweyd/dossard-pei            BRANCH        main
//   ADMIN_PASSWORD (secret) mot de passe de l'admin, 12 caractères minimum
//   GITHUB_TOKEN   (secret) clé GitHub limitée au dépôt, droit « Contents : lecture et écriture »
//   GC_SITE        dossardpei                     GC_TOKEN      (secret, facultatif) clé « lecture des statistiques »
//   CF_ACCOUNT     identifiant du compte          CF_ZONE       identifiant de la zone dossardpei.re
//   CF_SITE_TAG    identifiant du site Web Analytics
//   CF_API_TOKEN   (secret, facultatif) jeton « Analytics : lecture » (compte et zone)
//   MSG            espace de stockage KV (liaison « KV namespace ») pour les messages des formulaires
//   SALT           (secret) texte au hasard, pour compter les envois par appareil sans garder l'adresse IP

const WRITE = /^(data\.json|state\/overrides\.json|clubs\/clubs\.json|saison2027\.json|posters\/in\/[a-z0-9-]+\.(jpg|png))$/;
const READ = /^(data\.json|saison2027\.json|clubs\/clubs\.json|state\/[a-z0-9_-]+\.json)$/;
const GC_PATHS = /^stats\/(total|hits|toprefs|browsers|systems|sizes|locations|campaigns)(\/[\w%.+-]{1,120})?$/;   // + niveau de détail (une page, un navigateur, un pays…)
const MAX = 4_000_000;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === "/api/form") return form(req, env);
    const path = url.pathname.replace(/^\/admin\/api\/?/, "");
    if (path === "login" && req.method === "POST") return login(req, env);
    if (path === "logout") return json({ ok: true }, 200, { "set-cookie": "dp_admin=; Path=/admin; Max-Age=0; HttpOnly; Secure; SameSite=Strict" });
    let who = await session(req, env).catch(() => null);
    if (!who) { try { who = await access(req, env); } catch (e) { who = null; } }
    if (!who) return json({ error: "connexion nécessaire", login: true }, 401);
    if (req.method === "POST" && req.headers.get("x-admin") !== "1") return json({ error: "requête refusée" }, 400);
    try {
      if (path === "me") return json({ email: who, gc: !!env.GC_TOKEN, cf: !!(env.CF_API_TOKEN && env.CF_ACCOUNT) });
      if (path === "files" && req.method === "GET") return json(await files(env, (url.searchParams.get("paths") || "").split(",")));
      if (path === "commit" && req.method === "POST") return await commit(env, await req.json());
      if (path === "history") return json(await history(env));
      if (path.startsWith("gc/")) return await gc(env, path.slice(3), url.searchParams);
      if (path === "cf" && req.method === "POST") return await cf(env, await req.json());
      if (path === "messages" && req.method === "GET") return json(await messages(env));
      if (path.startsWith("messages/")) return await message(env, req, decodeURIComponent(path.slice(9)));
      return json({ error: "inconnu" }, 404);
    } catch (e) {
      return json({ error: String(e && e.message || e).slice(0, 300) }, 500);
    }
  },
};

const json = (o, status = 200, extra = {}) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });

// ---------- mot de passe ----------
const DAYS30 = 30 * 86400;
const hex = buf => [...new Uint8Array(buf)].map(x => x.toString(16).padStart(2, "0")).join("");
const sha = async t => hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t)));
async function sign(env, text) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode("dp-admin:" + env.ADMIN_PASSWORD + ":" + (env.SALT || "")), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(text)));
}
async function session(req, env) {
  if (!env.ADMIN_PASSWORD || env.ADMIN_PASSWORD.length < 12) return null;
  const m = (req.headers.get("cookie") || "").match(/(?:^|;\s*)dp_admin=(\d+)\.([0-9a-f]{64})/);
  if (!m || +m[1] < Date.now() / 1000) return null;
  return (await sign(env, m[1])) === m[2] ? "admin" : null;
}
const FAILS = new Map();   // secours si l'espace KV n'est pas relié
async function login(req, env) {
  if (!env.ADMIN_PASSWORD || env.ADMIN_PASSWORD.length < 12) return json({ error: "Mot de passe non réglé dans Cloudflare (12 caractères minimum)." }, 503);
  const h = (await sha((env.SALT || "dp") + (req.headers.get("cf-connecting-ip") || ""))).slice(0, 16), k = `lg:${h}:${Math.floor(Date.now() / 3600e3)}`;
  const n = env.MSG ? +(await env.MSG.get(k)) || 0 : FAILS.get(k) || 0;
  if (n >= 5) return json({ error: "Trop d'essais. Réessaie dans une heure." }, 429);
  let b = {}; try { b = await req.json(); } catch { }
  const ok = (await sha(String(b.password || ""))) === (await sha(env.ADMIN_PASSWORD));
  if (!ok) {
    if (env.MSG) await env.MSG.put(k, String(n + 1), { expirationTtl: 3700 }); else FAILS.set(k, n + 1);
    await new Promise(r => setTimeout(r, 800));
    return json({ error: n + 1 >= 5 ? "Mot de passe incorrect. Trop d'essais : réessaie dans une heure." : `Mot de passe incorrect (${4 - n} essai${4 - n > 1 ? "s" : ""} restant${4 - n > 1 ? "s" : ""}).` }, 401);
  }
  const exp = String(Math.floor(Date.now() / 1000) + DAYS30);
  return json({ ok: true }, 200, { "set-cookie": `dp_admin=${exp}.${await sign(env, exp)}; Path=/admin; Max-Age=${DAYS30}; HttpOnly; Secure; SameSite=Strict` });
}

// ---------- Cloudflare Access ----------
let CERTS = null, CERTS_AT = 0;
const b64u = s => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), c => c.charCodeAt(0));
async function access(req, env) {
  const jwt = req.headers.get("cf-access-jwt-assertion");
  if (!jwt || !env.ACCESS_TEAM || !env.ACCESS_AUD) return null;
  const [h, p, s] = jwt.split(".");
  const head = JSON.parse(new TextDecoder().decode(b64u(h)));
  const body = JSON.parse(new TextDecoder().decode(b64u(p)));
  if (!CERTS || Date.now() - CERTS_AT > 3600e3 || !CERTS.find(k => k.kid === head.kid)) {
    CERTS = (await (await fetch(`https://${env.ACCESS_TEAM}/cdn-cgi/access/certs`)).json()).keys || [];
    CERTS_AT = Date.now();
  }
  const jwk = CERTS.find(k => k.kid === head.kid);
  if (!jwk) return null;
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64u(s), new TextEncoder().encode(`${h}.${p}`));
  const aud = [].concat(body.aud || []);
  if (!ok || !aud.includes(env.ACCESS_AUD) || body.exp * 1000 < Date.now() || body.iss !== `https://${env.ACCESS_TEAM}`) return null;
  const allowed = (env.ADMIN_EMAILS || "").toLowerCase().split(",").map(x => x.trim()).filter(Boolean);
  const email = String(body.email || "").toLowerCase();
  return allowed.includes(email) ? email : null;
}

// ---------- GitHub ----------
async function gh(env, method, path, body) {
  const r = await fetch(`https://api.github.com/repos/${env.REPO}${path}`, {
    method,
    headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json", "user-agent": "dossardpei-admin", "x-github-api-version": "2022-11-28", ...(body ? { "content-type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const t = await r.text();
  let j; try { j = t ? JSON.parse(t) : {}; } catch { j = { raw: t }; }
  if (!r.ok) { const e = new Error(`GitHub ${r.status} : ${j.message || ""}`); e.status = r.status; throw e; }
  return j;
}
const dec = b64 => new TextDecoder().decode(Uint8Array.from(atob(b64.replace(/\n/g, "")), c => c.charCodeAt(0)));
const enc = s => { const b = new TextEncoder().encode(s); let o = ""; for (let i = 0; i < b.length; i += 0x8000) o += String.fromCharCode(...b.subarray(i, i + 0x8000)); return btoa(o); };
const branch = env => env.BRANCH || "main";

async function head(env) {
  const ref = await gh(env, "GET", `/git/ref/heads/${branch(env)}`);
  const c = await gh(env, "GET", `/git/commits/${ref.object.sha}`);
  return { commit: ref.object.sha, tree: c.tree.sha };
}
async function shaAt(env, commit, path) {
  try { return (await gh(env, "GET", `/contents/${path}?ref=${commit}`)).sha; } catch (e) { if (e.status === 404) return null; throw e; }
}

async function files(env, paths) {
  const { commit } = await head(env);
  const out = {};
  for (const p of paths.filter(Boolean)) {
    if (!READ.test(p)) { out[p] = { error: "non autorisé" }; continue; }
    try {
      const c = await gh(env, "GET", `/contents/${p}?ref=${commit}`);
      const b64 = c.content || (await gh(env, "GET", `/git/blobs/${c.sha}`)).content;
      out[p] = { sha: c.sha, text: dec(b64) };
    } catch (e) { out[p] = { error: e.status === 404 ? "absent" : e.message }; }
  }
  return { commit, files: out };
}

// body: { message, base: {path: sha}, files: [{path, text} | {path, b64}] }
async function commit(env, body) {
  const list = body.files || [];
  if (!list.length || list.length > 6) return json({ error: "rien à enregistrer" }, 400);
  let size = 0;
  for (const f of list) {
    if (!WRITE.test(f.path)) return json({ error: `fichier non autorisé : ${f.path}` }, 400);
    if (f.text != null) { if (/\.json$/.test(f.path)) JSON.parse(f.text); size += f.text.length; }
    else if (f.b64) size += f.b64.length * 0.75; else return json({ error: "fichier vide" }, 400);
  }
  if (size > MAX) return json({ error: "fichiers trop lourds" }, 413);
  const msg = String(body.message || "Admin").replace(/\s+/g, " ").slice(0, 200);
  for (let i = 0; i < 3; i++) {
    const h = await head(env);
    for (const [p, sha] of Object.entries(body.base || {})) {
      if ((await shaAt(env, h.commit, p)) !== sha) return json({ conflict: p }, 409);   // le fichier a changé (synchro) : la page recharge et réapplique
    }
    const tree = [];
    for (const f of list) {
      const b = await gh(env, "POST", "/git/blobs", f.text != null ? { content: enc(f.text), encoding: "base64" } : { content: f.b64, encoding: "base64" });
      tree.push({ path: f.path, mode: "100644", type: "blob", sha: b.sha });
    }
    const t = await gh(env, "POST", "/git/trees", { base_tree: h.tree, tree });
    const c = await gh(env, "POST", "/git/commits", { message: `Admin : ${msg}`, tree: t.sha, parents: [h.commit], author: { name: "Dossard Pei", email: "noreply@dossardpei.re" } });
    try {
      await gh(env, "PATCH", `/git/refs/heads/${branch(env)}`, { sha: c.sha, force: false });
      return json({ ok: true, commit: c.sha });
    } catch (e) { if (e.status !== 422) throw e; }   // une autre mise à jour vient de passer : on recommence sur elle
  }
  return json({ conflict: "branche" }, 409);
}

async function history(env) {
  const l = await gh(env, "GET", `/commits?sha=${branch(env)}&per_page=40`);
  return l.map(c => ({ sha: c.sha, msg: c.commit.message.split("\n")[0], at: c.commit.author.date, url: c.html_url }));
}

// ---------- statistiques ----------
async function gc(env, p, q) {
  if (!env.GC_TOKEN) return json({ error: "compteur non relié" }, 404);
  if (!GC_PATHS.test(p)) return json({ error: "non autorisé" }, 400);
  const qs = new URLSearchParams();
  for (const k of ["start", "end", "limit", "offset"]) if (q.get(k)) qs.set(k, q.get(k));
  for (const k of ["include_paths", "exclude_paths"]) for (const v of q.getAll(k)) if (/^\d+(,\d+)*$/.test(v)) qs.append(k, v);   // « 1,2,3 » ou répété   // pagination : plusieurs valeurs
  const r = await fetch(`https://${env.GC_SITE || "dossardpei"}.goatcounter.com/api/v0/${p}?${qs}`, { headers: { authorization: `Bearer ${env.GC_TOKEN}`, "content-type": "application/json" } });
  return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

async function cf(env, body) {
  if (!env.CF_API_TOKEN) return json({ error: "statistiques Cloudflare non reliées" }, 404);
  const query = String(body.query || "");
  if (!/^\s*query\b/.test(query)) return json({ error: "non autorisé" }, 400);
  const variables = { ...(body.variables || {}), account: env.CF_ACCOUNT, zone: env.CF_ZONE, site: env.CF_SITE_TAG };
  const r = await fetch("https://api.cloudflare.com/client/v4/graphql", { method: "POST", headers: { authorization: `Bearer ${env.CF_API_TOKEN}`, "content-type": "application/json" }, body: JSON.stringify({ query, variables }) });
  return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

// ---------- formulaires du site ----------
const YEAR = 365 * 86400;
const TYPES = { contact: 1, "club-ajout": 1, "club-maj": 1, "club-correction": 1 };
const str = (v, n) => typeof v === "string" ? v.trim().slice(0, n) : "";
async function form(req, env) {
  const out = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
  if (req.method !== "POST" || !env.MSG) return out({ ok: false }, 503);   // le site passe alors par l'e-mail
  const origin = req.headers.get("origin") || "";
  if (origin && !/^https:\/\/(www\.)?dossardpei\.re$/.test(origin)) return out({ ok: false }, 403);
  const raw = await req.text();
  if (raw.length > 12000) return out({ ok: false, error: "trop long" }, 413);
  let b; try { b = JSON.parse(raw); } catch { return out({ ok: false }, 400); }
  if (b.botcheck) return out({ ok: true });   // piège à robots : on fait comme si
  const type = TYPES[b.type] ? b.type : "contact";
  const msg = { type, at: new Date().toISOString(), objet: str(b.objet, 120), sujet: str(b.sujet, 200), course: str(b.course, 200), club: str(b.club, 120), page: str(b.page, 300),
    message: str(b.message, 6000), nom: str(b.nom, 120), email: str(b.email, 200), champs: {}, etat: "nouveau" };
  for (const [k, v] of Object.entries(b.champs || {}).slice(0, 40)) if (typeof v === "string" && v.trim()) msg.champs[str(k, 60)] = str(v, 1000);
  if (msg.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(msg.email)) msg.email = "";
  if (!msg.message && !Object.keys(msg.champs).length) return out({ ok: false, error: "vide" }, 400);
  // au plus 6 envois par heure et par appareil (adresse IP hachée, jamais enregistrée en clair)
  const ip = req.headers.get("cf-connecting-ip") || "";
  const h = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode((env.SALT || "dp") + ip)))].slice(0, 8).map(x => x.toString(16).padStart(2, "0")).join("");
  const rk = `rl:${h}:${Math.floor(Date.now() / 3600e3)}`;
  const n = +(await env.MSG.get(rk)) || 0;
  if (n >= 6) return out({ ok: false, error: "trop d'envois" }, 429);
  await env.MSG.put(rk, String(n + 1), { expirationTtl: 3700 });
  const id = `m:${(9e15 - Date.now()).toString().padStart(16, "0")}:${crypto.randomUUID().slice(0, 6)}`;   // les plus récents d'abord
  await env.MSG.put(id, JSON.stringify(msg), { expirationTtl: YEAR, metadata: meta(msg) });
  return out({ ok: true });
}
const meta = m => ({ type: m.type, at: m.at, etat: m.etat, t: (m.sujet || m.objet || "").slice(0, 80), c: (m.course || m.club || "").slice(0, 80), x: (m.message || "").slice(0, 160) });
async function messages(env) {
  if (!env.MSG) return { error: "espace des messages non relié", list: [] };
  const list = []; let cursor;
  do { const r = await env.MSG.list({ prefix: "m:", cursor, limit: 1000 }); for (const k of r.keys) list.push({ id: k.name, ...(k.metadata || {}), exp: k.expiration }); cursor = r.list_complete ? null : r.cursor; } while (cursor && list.length < 3000);
  return { list };
}
async function message(env, req, id) {
  if (!env.MSG || !/^m:\d{16}:[0-9a-f]{6}$/.test(id)) return json({ error: "inconnu" }, 404);
  const { value, metadata } = await env.MSG.getWithMetadata(id);
  if (value == null) return json({ error: "message introuvable" }, 404);
  const m = JSON.parse(value);
  if (req.method === "GET") return json({ id, ...m });
  if (req.method === "DELETE") { await env.MSG.delete(id); return json({ ok: true }); }
  if (req.method === "POST") {
    const b = await req.json();
    if (["nouveau", "traite"].includes(b.etat)) m.etat = b.etat;
    // garde l'échéance d'origine (un an après l'envoi)
    const left = Math.max(60, Math.round((Date.parse(m.at) + YEAR * 1000 - Date.now()) / 1000));
    await env.MSG.put(id, JSON.stringify(m), { expirationTtl: left, metadata: meta(m) });
    return json({ ok: true });
  }
  return json({ error: "requête refusée" }, 400);
}
