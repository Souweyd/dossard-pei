// Dossard Péi — service de la page admin (Cloudflare Worker, route dossardpei.re/admin/api/*).
//
// Seule la personne autorisée par Cloudflare Access (code reçu par e-mail) passe : chaque requête
// porte le jeton signé d'Access, vérifié ici (signature, audience, expiration, adresse autorisée).
// Le service lit et écrit les fichiers de données du dépôt GitHub en un seul commit, et relaie les
// statistiques (compteur d'audience, Web Analytics). Aucune clé n'est dans ce fichier : elles sont
// des « secrets » du Worker, saisis par le propriétaire dans Cloudflare.
//
// Variables (Paramètres › Variables et secrets) :
//   REPO           Souweyd/dossard-pei            BRANCH        main
//   ACCESS_TEAM    <équipe>.cloudflareaccess.com  ACCESS_AUD    étiquette d'audience de l'application Access
//   ADMIN_EMAILS   adresse(s) autorisée(s), séparées par des virgules
//   GITHUB_TOKEN   (secret) clé GitHub limitée au dépôt, droit « Contents : lecture et écriture »
//   GC_SITE        dossardpei                     GC_TOKEN      (secret, facultatif) clé « lecture des statistiques »
//   CF_ACCOUNT     identifiant du compte          CF_ZONE       identifiant de la zone dossardpei.re
//   CF_SITE_TAG    identifiant du site Web Analytics
//   CF_API_TOKEN   (secret, facultatif) jeton « Analytics : lecture » (compte et zone)

const WRITE = /^(data\.json|state\/overrides\.json|clubs\/clubs\.json|saison2027\.json|posters\/in\/[a-z0-9-]+\.(jpg|png))$/;
const READ = /^(data\.json|saison2027\.json|clubs\/clubs\.json|state\/[a-z0-9_-]+\.json)$/;
const GC_PATHS = /^(stats\/(total|hits|toprefs|browsers|systems|sizes|locations|campaigns)|stats\/hits\/\d+|stats\/toprefs\/\d+)$/;
const MAX = 4_000_000;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/^\/admin\/api\/?/, "");
    let who;
    try { who = await access(req, env); } catch (e) { who = null; }
    if (!who) return json({ error: "accès refusé" }, 403);
    if (req.method === "POST" && req.headers.get("x-admin") !== "1") return json({ error: "requête refusée" }, 400);
    try {
      if (path === "me") return json({ email: who, gc: !!env.GC_TOKEN, cf: !!(env.CF_API_TOKEN && env.CF_ACCOUNT) });
      if (path === "files" && req.method === "GET") return json(await files(env, (url.searchParams.get("paths") || "").split(",")));
      if (path === "commit" && req.method === "POST") return await commit(env, await req.json());
      if (path === "history") return json(await history(env));
      if (path.startsWith("gc/")) return await gc(env, path.slice(3), url.searchParams);
      if (path === "cf" && req.method === "POST") return await cf(env, await req.json());
      return json({ error: "inconnu" }, 404);
    } catch (e) {
      return json({ error: String(e && e.message || e).slice(0, 300) }, 500);
    }
  },
};

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });

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
  for (const k of ["start", "end", "limit", "include_paths", "exclude_paths", "offset"]) if (q.get(k)) qs.set(k, q.get(k));
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
