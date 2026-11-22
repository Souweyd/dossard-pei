# Page admin : mise en route

L'adresse de la page est **https://dossardpei.re/admin/**.
- La page est protégée par **Cloudflare Access** : seule ton adresse e-mail peut entrer, avec un code reçu par mail.
- Les enregistrements passent par un petit **service Cloudflare (Worker)**. Il écrit dans le dépôt GitHub avec une clé limitée à ce dépôt.
- Les clés ne sont jamais dans le code. Ce sont des « secrets » du Worker, que tu saisis toi-même.

Il y a deux étapes. La première est indispensable, la seconde ajoute les statistiques.

---

## Étape 1 : l'admin (environ 20 minutes)

### 1. La clé GitHub
1. Sur github.com, clique sur ta photo, puis **Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token**.
2. Remplis les champs :
   - **Nom** : `Admin Dossard Péi`.
   - **Expiration** : 1 an. Note la date : il faudra la renouveler.
   - **Repository access** : *Only select repositories*, puis **Souweyd/dossard-pei**.
   - **Permissions › Repository permissions › Contents** : *Read and write*. Le reste ne change pas.
3. Clique sur **Generate token** et copie la clé (elle commence par `github_pat_`). Garde-la le temps de l'étape 3 et ne l'envoie à personne.

### 2. La protection par code e-mail (Cloudflare Access)
1. Dans Cloudflare, ouvre **Zero Trust** (menu de gauche de l'accueil du compte).
   - La première fois, choisis un **nom d'équipe**, par exemple `dossardpei`. Ton adresse d'équipe sera `dossardpei.cloudflareaccess.com`.
   - Choisis l'offre **Free** (jusqu'à 50 personnes). Cloudflare peut demander une carte, mais rien n'est facturé avec l'offre Free.
2. Va dans **Access › Applications › Add an application › Self-hosted** et remplis :
   - **Application name** : `Admin Dossard Péi`.
   - **Session duration** : `1 month` (ou moins si tu préfères).
   - **Domaine** : `dossardpei.re`, avec le **chemin** `admin`.
3. Crée une **Policy** :
   - **Nom** : `Moi`.
   - **Action** : *Allow*.
   - **Include › Emails** : ton adresse.
4. Garde la **connexion par code à usage unique** (*One-time PIN*), qui est proposée par défaut, et enregistre.
5. Dans l'application créée, copie l'**Application Audience (AUD) Tag** : c'est une longue suite de lettres et de chiffres.

### 3. Le service (Worker)
1. Dans Cloudflare, ouvre **Workers & Pages › Create › Worker**.
2. Nomme-le `dossardpei-admin`, puis clique sur **Deploy**.
3. Clique sur **Edit code**, efface tout, colle le contenu de `tools/admin-worker.js`, puis clique sur **Deploy**.
4. Va dans **Settings › Variables and Secrets** et ajoute ces variables :

| Nom | Type | Valeur |
|---|---|---|
| `REPO` | Text | `Souweyd/dossard-pei` |
| `BRANCH` | Text | `main` |
| `ACCESS_TEAM` | Text | `dossardpei.cloudflareaccess.com` (ton nom d'équipe) |
| `ACCESS_AUD` | Text | le tag AUD copié à l'étape 2 |
| `ADMIN_EMAILS` | Text | ton adresse (la même que dans la policy) |
| `GITHUB_TOKEN` | **Secret** | la clé GitHub de l'étape 1 |

5. Va dans **Settings › Domains & Routes › Add › Route** :
   - **Route** : `dossardpei.re/admin/api/*`.
   - **Zone** : `dossardpei.re`.
6. Ouvre https://dossardpei.re/admin/, saisis ton adresse e-mail, puis le code reçu : l'admin s'ouvre.

---

## Étape 2 : les stats (environ 10 minutes, facultatif)

### Visites et clics (compteur d'audience)
1. Sur dossardpei.goatcounter.com, va dans **Settings › API**, crée une nouvelle clé et coche seulement **Read statistics**.
2. Dans le Worker, ajoute :
   - `GC_SITE` (Text) : `dossardpei` ;
   - `GC_TOKEN` (**Secret**) : la clé.

### Vitesse réelle et trafic (Cloudflare)
1. Dans Cloudflare, va dans **Mon profil › API Tokens › Create Token › Custom token**.
2. Donne-lui deux permissions :
   - **Account › Account Analytics › Read** ;
   - **Zone › Analytics › Read**, limitée à `dossardpei.re`.
3. Dans le Worker, ajoute :
   - `CF_API_TOKEN` (**Secret**) : le jeton ;
   - `CF_ACCOUNT` (Text) : l'identifiant du compte. C'est la suite de 32 caractères dans l'adresse du tableau de bord, juste après `dash.cloudflare.com/`.
   - `CF_ZONE` (Text) : le **Zone ID**, affiché en bas à droite de la page « Vue d'ensemble » de dossardpei.re.
   - `CF_SITE_TAG` (Text) : ouvre Web Analytics pour dossardpei.re et copie la valeur qui suit `siteTag` dans la barre d'adresse.

---

## Bon à savoir
- **Mise en ligne.** Chaque enregistrement crée une mise à jour « Admin : … » dans l'historique du dépôt. Le site est à jour 1 à 2 minutes plus tard, 3 minutes pour une affiche.
- **Verrouillage.** Seule l'info modifiée dans l'admin est **verrouillée** : la synchro horaire ne l'écrase plus, le reste continue de suivre les sources.
  - Pour une course, c'est un champ : la commune, une date, un lien…
  - Pour une épreuve, c'est une seule info : par exemple l'heure du 10 km.
  - Ajouter, retirer, renommer ou déplacer une épreuve verrouille toute la liste des épreuves.
  - Le bouton 🔒 « verrouillé », à côté de l'info, rend la main à la synchro, qui reprend la valeur de l'organisateur dans l'heure.
- **Retour arrière.** Une erreur se corrige dans l'admin. Sinon, l'historique du dépôt garde toutes les versions.
- **En cas de souci.** Si tu perds ton accès, tu peux couper l'admin en supprimant la route du Worker. Le site public n'est pas touché.
- **Logos des clubs.** Ils ne se changent pas dans l'admin (ils sont sur une planche commune) : il faut me les envoyer.
