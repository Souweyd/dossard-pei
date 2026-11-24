// Dossard Péi — service de la page admin (Cloudflare Worker, routes dossardpei.re/admin/api/*, dossardpei.re/api/form et dossardpei.re/api/push/*).
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
//   DB             base D1 (liaison « D1 database ») pour les notifications ; déclencheur cron « 20 * * * * »
//   SALT           (secret) texte au hasard, pour compter les envois par appareil sans garder l'adresse IP

const WRITE = /^(data\.json|state\/overrides\.json|clubs\/clubs\.json|saison2027\.json|posters\/in\/[a-z0-9-]+\.(jpg|png))$/;
const READ = /^(data\.json|saison2027\.json|clubs\/clubs\.json|state\/[a-z0-9_-]+\.json)$/;
const GC_PATHS = /^stats\/(total|hits|toprefs|browsers|systems|sizes|locations|campaigns)(\/[\w%.+-]{1,120})?$/;   // + niveau de détail (une page, un navigateur, un pays…)
const MAX = 4_000_000;

export default {
  async scheduled(event, env, ctx) { ctx.waitUntil(sendRun(env).catch(e => console.log("notifications", e))); },
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === "/api/form") return form(req, env);
    if (url.pathname.startsWith("/api/push/")) return pushApi(req, env, url.pathname.slice(10));
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
      if (path === "push" || path.startsWith("push/")) return await pushAdmin(req, env, path);
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

// ---------- notifications (Web Push) ----------
// Base D1 (liaison DB) : abonnements, journal des envois, état. Les clés d'envoi (VAPID) sont créées par le service
// lui-même au premier usage et gardées dans la base : aucune clé à saisir.
// Tâche horaire (déclencheur cron « 20 * * * * ») : lit le journal des changements du site et envoie, entre 7 h et 21 h
// (heure de La Réunion) ; rappels et clôtures à 18 h. Plus de 3 nouveaux dossards d'un coup : une seule notification.
const SITE = "https://dossardpei.re";
const TZ = 4 * 3600e3;   // La Réunion, UTC+4, sans heure d'été
const PREFS = { nouveau: 1, ouverture: 1, places: 1, cloture: 1, changement: 1, annul: 1, rappel: 1 };
const PUSH_HOSTS = /^https:\/\/([a-z0-9.-]+\.)?(fcm\.googleapis\.com|push\.services\.mozilla\.com|push\.apple\.com|notify\.windows\.com|push\.api\.chromium\.org)\//;
const enc64u = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const dec64u = s => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), c => c.charCodeAt(0));
const cat = (...a) => { const o = new Uint8Array(a.reduce((n, x) => n + x.length, 0)); let i = 0; for (const x of a) { o.set(x, i); i += x.length; } return o; };
const te = s => new TextEncoder().encode(s);
async function hmac(key, data) { const k = await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]); return new Uint8Array(await crypto.subtle.sign("HMAC", k, data)); }

let DBREADY = false;
async function db(env) {
  if (!env.DB) throw new Error("base des notifications non reliée");
  if (!DBREADY) {
    await env.DB.batch([
      env.DB.prepare("CREATE TABLE IF NOT EXISTS subs (id TEXT PRIMARY KEY, endpoint TEXT NOT NULL, p256dh TEXT NOT NULL, auth TEXT NOT NULL, favs TEXT NOT NULL DEFAULT '[]', prefs TEXT NOT NULL DEFAULT '{}', created TEXT, updated TEXT, day TEXT, sent INTEGER DEFAULT 0, fails INTEGER DEFAULT 0, admin INTEGER DEFAULT 0)"),
      env.DB.prepare("CREATE TABLE IF NOT EXISTS sends (n INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, race TEXT, title TEXT, body TEXT, sent INTEGER, ok INTEGER, gone INTEGER)"),
      env.DB.prepare("CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT)"),
    ]);
    DBREADY = true;
  }
  return env.DB;
}
const getState = async (env, k) => { const r = await (await db(env)).prepare("SELECT v FROM state WHERE k = ?").bind(k).first(); return r ? JSON.parse(r.v) : null; };
const setState = async (env, k, v) => (await db(env)).prepare("INSERT INTO state (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(k, JSON.stringify(v)).run();

// clés VAPID (ES256), créées une fois
async function vapid(env) {
  let k = await getState(env, "vapid");
  if (!k) {
    const p = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
    k = { priv: await crypto.subtle.exportKey("jwk", p.privateKey), pub: enc64u(await crypto.subtle.exportKey("raw", p.publicKey)) };
    await setState(env, "vapid", k);
  }
  return k;
}
async function vapidHeader(env, endpoint) {
  const k = await vapid(env);
  const head = enc64u(te(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const body = enc64u(te(JSON.stringify({ aud: new URL(endpoint).origin, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: "mailto:contact@dossardpei.re" })));
  const key = await crypto.subtle.importKey("jwk", k.priv, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, te(`${head}.${body}`));
  return `vapid t=${head}.${body}.${enc64u(sig)}, k=${k.pub}`;
}
// chiffrement du message (RFC 8291, aes128gcm)
async function encrypt(p256dh, auth, text) {
  const ua = dec64u(p256dh), secret = dec64u(auth);
  const eph = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const asPub = new Uint8Array(await crypto.subtle.exportKey("raw", eph.publicKey));
  const uaKey = await crypto.subtle.importKey("raw", ua, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: uaKey }, eph.privateKey, 256));
  const prkKey = await hmac(secret, shared);
  const ikm = await hmac(prkKey, cat(te("WebPush: info\0"), ua, asPub, new Uint8Array([1])));
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const prk = await hmac(salt, ikm);
  const cek = (await hmac(prk, cat(te("Content-Encoding: aes128gcm\0"), new Uint8Array([1])))).slice(0, 16);
  const nonce = (await hmac(prk, cat(te("Content-Encoding: nonce\0"), new Uint8Array([1])))).slice(0, 12);
  const k = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, k, cat(te(text), new Uint8Array([2]))));
  return cat(salt, new Uint8Array([0, 0, 16, 0]), new Uint8Array([65]), asPub, ct);   // en-tête : sel, taille d'enregistrement 4096, clé
}
// envoie un message à un abonnement ; "gone" = l'appareil n'existe plus (on supprime l'abonnement)
async function pushOne(env, s, msg) {
  try {
    const r = await fetch(s.endpoint, {
      method: "POST",
      headers: { authorization: await vapidHeader(env, s.endpoint), "content-encoding": "aes128gcm", "content-type": "application/octet-stream", ttl: String(msg.ttl || 86400), urgency: msg.urgency || "normal", ...(msg.topic ? { topic: msg.topic } : {}) },
      body: await encrypt(s.p256dh, s.auth, JSON.stringify(msg)),
    });
    if (r.status === 404 || r.status === 410) return "gone";
    return r.ok ? "ok" : "fail:" + r.status;
  } catch (e) { return "fail"; }
}

// ----- abonnement depuis le site (public) -----
async function pushApi(req, env, path) {
  const out = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
  try {
    if (path === "key") return out({ key: (await vapid(env)).pub });
    if (req.method !== "POST") return out({ error: "requête refusée" }, 405);
    const origin = req.headers.get("origin") || "";
    if (origin && !/^https:\/\/(www\.)?dossardpei\.re$/.test(origin)) return out({ error: "refusé" }, 403);
    const raw = await req.text();
    if (raw.length > 20000) return out({ error: "trop long" }, 413);
    const b = JSON.parse(raw || "{}");
    const sub = b.subscription || {}, ep = String(sub.endpoint || b.endpoint || "");
    if (!PUSH_HOSTS.test(ep) || ep.length > 1000) return out({ error: "abonnement invalide" }, 400);
    const id = (await sha(ep)).slice(0, 32), D = await db(env), now = new Date().toISOString();
    if (path === "unsub") { await D.prepare("DELETE FROM subs WHERE id = ?").bind(id).run(); return out({ ok: true }); }
    if (path !== "sub") return out({ error: "inconnu" }, 404);
    const p256dh = String(sub.keys?.p256dh || ""), auth = String(sub.keys?.auth || "");
    if (!/^[\w-]{80,100}$/.test(p256dh) || !/^[\w-]{16,30}$/.test(auth)) return out({ error: "clés invalides" }, 400);
    let favs = [...new Set((Array.isArray(b.favs) ? b.favs : []).filter(x => typeof x === "string" && /^[a-z0-9-]{2,80}$/.test(x)))].slice(0, 300);
    const prefs = {}; for (const k in PREFS) prefs[k] = b.prefs && k in b.prefs ? (b.prefs[k] ? 1 : 0) : 1;
    if (b.old && PUSH_HOSTS.test(String(b.old))) {   // abonnement renouvelé par le navigateur : on reprend les favoris et réglages de l'ancien
      const oid = (await sha(String(b.old))).slice(0, 32), o = await D.prepare("SELECT favs, prefs FROM subs WHERE id = ?").bind(oid).first();
      if (o) { favs = JSON.parse(o.favs || "[]"); Object.assign(prefs, JSON.parse(o.prefs || "{}")); if (oid !== id) await D.prepare("DELETE FROM subs WHERE id = ?").bind(oid).run(); }
    }
    await D.prepare(`INSERT INTO subs (id, endpoint, p256dh, auth, favs, prefs, created, updated, fails) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
      ON CONFLICT(id) DO UPDATE SET endpoint = excluded.endpoint, p256dh = excluded.p256dh, auth = excluded.auth, favs = excluded.favs, prefs = excluded.prefs, updated = excluded.updated, fails = 0`)
      .bind(id, ep, p256dh, auth, JSON.stringify(favs), JSON.stringify(prefs), now, now).run();
    if (b.welcome) {   // première activation : petite notification de confirmation (elle prouve que tout marche)
      await pushOne(env, { endpoint: ep, p256dh, auth }, { title: "Notifications activées 🔔", body: favs.length ? `Tu seras prévenu pour tes ${favs.length} course${favs.length > 1 ? "s" : ""} favorite${favs.length > 1 ? "s" : ""}.` : "Tu seras prévenu des nouveaux dossards.", url: "/?ref=notif-bienvenue", tag: "bienvenue" });
    }
    return out({ ok: true });
  } catch (e) { return out({ error: String(e.message || e).slice(0, 200) }, 500); }
}

// ----- envoi : tâche horaire -----
const reu = (ms = Date.now()) => new Date(ms + TZ);   // date et heure de La Réunion (lire avec getUTC…)
const dayStr = d => d.toISOString().slice(0, 10);
const addDays = (d, n) => dayStr(new Date(Date.parse(d + "T12:00:00Z") + n * 864e5));
const MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
const fdate = d => { const x = new Date(d + "T12:00:00Z"); return `${JOURS[x.getUTCDay()]} ${x.getUTCDate()} ${MOIS[x.getUTCMonth()]}`; };
const dist = r => [...new Set((r.epreuves || []).map(e => e.km).filter(Boolean))].sort((a, b) => a - b).map(k => String(k).replace(".", ",") + " km").slice(0, 5).join(", ");
const getJSON = async u => (await fetch(`${SITE}/${u}?c=${Date.now()}`, { headers: { "user-agent": "Mozilla/5.0 (compatible; DossardPei-notifications/1.0; +https://dossardpei.re)" } })).json();

async function sendRun(env, opts = {}) {
  const now = reu(), h = now.getUTCHours(), today = dayStr(now);
  if (!opts.force && (h < 7 || h >= 21)) return { skipped: "nuit" };   // silence la nuit : le journal attendra 7 h
  const D = await db(env);
  const [journal, data] = [await getJSON("state/journal.json"), await getJSON("data.json")];
  const races = Object.fromEntries((data.races || []).map(r => [r.id, r]));
  // 1. événements du journal pas encore traités
  const key = e => `${e.at}|${e.t}|${e.id}|${e.a || ""}`;
  let seen = await getState(env, "seen");
  if (!seen) { await setState(env, "seen", journal.map(key)); return { init: journal.length }; }   // première fois : on ne rejoue pas le passé
  const S = new Set(seen), fresh = journal.filter(e => !S.has(key(e)));
  const msgs = [];   // { kind, race, fav: bool, title, body, url, ins }
  const url = (id, k) => `/course/${id}/?ref=notif-${k}`;
  const lastSent = async (kind, race, hours) => !!(await D.prepare("SELECT 1 FROM sends WHERE kind = ? AND race = ? AND at > ? LIMIT 1").bind(kind, race, new Date(Date.now() - hours * 3600e3).toISOString()).first());
  const chg = {};
  for (const e of fresh) {
    const r = races[e.id];
    if (e.t === "ajout" && r && !r.hidden) msgs.push({ kind: "nouveau", race: e.id, fav: false, title: `Nouveau dossard : ${r.nom}`, body: `${fdate(r.date)} · ${r.commune}${dist(r) ? " · " + dist(r) : ""}`, url: url(e.id, "nouveau"), image: r.poster_lg ? `${SITE}/${r.poster_lg}` : undefined });
    else if (e.t === "ouverture" && r) msgs.push({ kind: "ouverture", race: e.id, fav: true, title: r.nom, body: `Les inscriptions sont ouvertes${dist(r) ? " · " + dist(r) : ""}`, url: url(e.id, "ouverture"), ins: r.inscription });
    else if (e.t === "réouvert" && r && !r.complet && !(await lastSent("places", e.id, 12))) {
      // anti yo-yo : la course doit être encore ouverte maintenant, et au plus un message toutes les 12 h
      const age = Date.now() - Date.parse(e.at);
      if (age < 50 * 60e3) continue;   // trop récent : on revérifiera à la prochaine heure
      msgs.push({ kind: "places", race: e.id, fav: true, title: r.nom, body: "Des places se sont libérées : inscriptions rouvertes", url: url(e.id, "places"), ins: r.inscription });
    } else if (["date", "heure", "lieu", "distance", "dénivelé"].includes(e.t) && r) {
      const lib = { date: "Date", heure: "Heure", lieu: "Lieu", distance: "Distance", "dénivelé": "Dénivelé" }[e.t];
      const hh = x => String(x).replace(/^0/, "").replace("h", " h ").replace(/ h 00$/, " h").trim();
      const v = e.t === "date" ? `${fdate(e.de)} → ${fdate(e.a)}` : e.t === "heure" ? `${hh(e.de)} → ${hh(e.a)}` : `${e.de} → ${e.a}`;
      const part = e.nom.includes(" – ") ? e.nom.split(" – ").slice(1).join(" – ") + " : " : "";
      (chg[e.id] = chg[e.id] || []).push(`${lib} ${part}${v}`);
    }
    S.add(key(e));
  }
  for (const [id, l] of Object.entries(chg)) msgs.push({ kind: "changement", race: id, fav: true, title: `Changement : ${races[id].nom}`, body: l.slice(0, 3).join(" · "), url: url(id, "changement") });
  // 2. annulations (repérées dans les données : la course reste affichée avec le tampon)
  const ann = new Set((await getState(env, "annules")) || []);
  for (const r of data.races || []) if (r.annule && !ann.has(r.id)) { ann.add(r.id); if ((r.fin || r.date) >= today) msgs.push({ kind: "annul", race: r.id, fav: true, title: r.nom, body: "Course annulée par l'organisateur", url: url(r.id, "annul"), urgency: "high" }); }
  // 3. à 18 h : clôture des inscriptions demain, et rappel 2 jours avant la course
  if (h === 18 || opts.evening) {
    const done = (await getState(env, "soir")) || "";
    if (done !== today) {
      const tom = addDays(today, 1), j2 = addDays(today, 2);
      let meteo = {}; try { meteo = (await getJSON("weather.json")).races || {}; } catch (e) { }
      for (const r of data.races || []) {
        if (r.hidden) continue;
        if (r.limite === tom && !r.complet) msgs.push({ kind: "cloture", race: r.id, fav: true, title: r.nom, body: "Clôture des inscriptions demain", url: url(r.id, "cloture"), ins: r.inscription });
        if (r.date === j2) {
          const hs = [...new Set((r.epreuves || []).map(e => e.h).filter(Boolean))].sort();
          const w = (meteo[r.id] || [])[0], wt = w && w.window ? ` · ${w.window.tmin === w.window.tmax ? w.window.tmin : w.window.tmin + "-" + w.window.tmax}°C${w.window.rain >= 1 ? ", pluie possible" : ""}` : "";
          msgs.push({ kind: "rappel", race: r.id, fav: true, title: `${JOURS[new Date(r.date + "T12:00:00Z").getUTCDay()].replace(/^./, c => c.toUpperCase())} : ${r.nom}`, body: `${hs.length ? (hs.length > 1 ? "Premier départ " : "Départ ") + hs[0].replace(/^0/, "").replace("h", " h ").replace(/ h 00$/, " h") + " · " : ""}${r.lieu || r.commune}${wt}`, url: url(r.id, "rappel") });
        }
      }
      await setState(env, "soir", today);
    }
  }
  // 4. distribution : chaque abonné reçoit ce qui le concerne
  const res = { messages: msgs.length, envois: 0, ok: 0, supprimes: 0 };
  if (msgs.length) {
    const subs = (await D.prepare("SELECT * FROM subs").all()).results || [];
    const tally = {};
    for (const s of subs) {
      const favs = new Set(JSON.parse(s.favs || "[]")), prefs = { ...PREFS, ...JSON.parse(s.prefs || "{}") };
      const ORD = { annul: 0, places: 1, ouverture: 2, cloture: 3, changement: 4, rappel: 5, nouveau: 6 };   // le plus important d'abord
      const mine = msgs.filter(m => prefs[m.kind] && (!m.fav || favs.has(m.race))).sort((a, b) => ORD[a.kind] - ORD[b.kind]);
      if (!mine.length) continue;
      const sentToday = s.day === today ? s.sent : 0;
      // pas de plafond ; seule sécurité : plus de 3 nouveaux dossards d'un coup partent en une seule notification
      const nv = mine.filter(m => m.kind === "nouveau");
      const list = nv.length <= 3 ? mine : [...mine.filter(m => m.kind !== "nouveau"), { kind: "nouveau", race: "", title: `${nv.length} nouveaux dossards`, body: nv.map(m => m.title.replace(/^Nouveau dossard : /, "")).slice(0, 4).join(", ") + (nv.length > 4 ? "…" : ""), url: "/?ref=notif-nouveau" }];
      let n = 0, gone = false;
      for (const m of list) {
        const st = await pushOne(env, s, { title: m.title, body: m.body, url: m.url, ins: m.ins, image: m.image, tag: m.race ? `${m.kind}-${m.race}` : m.kind, topic: m.race ? (m.kind + m.race).replace(/[^\w-]/g, "").slice(-32) : undefined, urgency: m.urgency });
        const t = tally[m.kind + "|" + m.race] = tally[m.kind + "|" + m.race] || { m, sent: 0, ok: 0, gone: 0 };
        t.sent++; res.envois++;
        if (st === "ok") { t.ok++; res.ok++; n++; } else if (st === "gone") { t.gone++; gone = true; break; }
      }
      if (gone) { await D.prepare("DELETE FROM subs WHERE id = ?").bind(s.id).run(); res.supprimes++; }
      else await D.prepare("UPDATE subs SET day = ?, sent = ?, fails = CASE WHEN ? = 0 THEN fails + 1 ELSE 0 END WHERE id = ?").bind(today, sentToday + n, n, s.id).run();
    }
    const at = new Date().toISOString();
    for (const t of Object.values(tally)) await D.prepare("INSERT INTO sends (at, kind, race, title, body, sent, ok, gone) VALUES (?, ?, ?, ?, ?, ?, ?, ?)").bind(at, t.m.kind, t.m.race, t.m.title, t.m.body, t.sent, t.ok, t.gone).run();
    for (const m of msgs) if (!Object.keys(tally).includes(m.kind + "|" + m.race)) await D.prepare("INSERT INTO sends (at, kind, race, title, body, sent, ok, gone) VALUES (?, ?, ?, ?, ?, 0, 0, 0)").bind(at, m.kind, m.race, m.title, m.body).run();
  }
  // mémoire : 60 jours de journal suffisent ; on ne garde que les clés encore présentes
  const keys = new Set(journal.map(key));
  await setState(env, "seen", [...S].filter(k => keys.has(k)));
  await setState(env, "annules", [...ann].filter(id => races[id]));
  await D.prepare("DELETE FROM subs WHERE fails > 30").run();
  await D.prepare("DELETE FROM sends WHERE at < ?").bind(new Date(Date.now() - 180 * 864e5).toISOString()).run();
  return res;
}

// ----- admin -----
async function pushAdmin(req, env, path) {
  const D = await db(env);
  if (path === "push" && req.method === "GET") {
    const subs = (await D.prepare("SELECT favs, prefs, created, updated, day, sent, admin FROM subs").all()).results || [];
    const by = {}; for (const k in PREFS) by[k] = 0;
    const favCount = {};
    for (const s of subs) { const p = { ...PREFS, ...JSON.parse(s.prefs || "{}") }; for (const k in PREFS) if (p[k]) by[k]++; for (const f of JSON.parse(s.favs || "[]")) favCount[f] = (favCount[f] || 0) + 1; }
    const sends = (await D.prepare("SELECT * FROM sends ORDER BY n DESC LIMIT 60").all()).results || [];
    const week = new Date(Date.now() - 7 * 864e5).toISOString();
    return json({ abonnes: subs.length, nouveaux7j: subs.filter(s => (s.created || "") >= week).length, actifs7j: subs.filter(s => (s.updated || "") >= week).length, prefs: by, favoris: Object.entries(favCount).sort((a, b) => b[1] - a[1]).slice(0, 15), envois: sends, cle: (await vapid(env)).pub });
  }
  if (path === "push/test" && req.method === "POST") {
    const b = await req.json(), id = (await sha(String(b.endpoint || ""))).slice(0, 32);
    const s = await D.prepare("SELECT * FROM subs WHERE id = ?").bind(id).first();
    if (!s) return json({ error: "Cet appareil n'est pas abonné : active d'abord les notifications ici." }, 404);
    await D.prepare("UPDATE subs SET admin = 1 WHERE id = ?").bind(id).run();
    const st = await pushOne(env, s, { title: "Test Dossard Péi 🔔", body: "Si tu lis ceci, les notifications marchent sur cet appareil.", url: "/admin/", tag: "test" });
    return json({ ok: st === "ok", statut: st });
  }
  if (path === "push/run" && req.method === "POST") { const b = await req.json().catch(() => ({})); return json(await sendRun(env, { force: true, evening: !!b.soir })); }
  return json({ error: "inconnu" }, 404);
}
