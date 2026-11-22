# Page admin : mise en route

> **État au 22/11/2026, 18 h 15** : l'étape 1 est faite et fonctionne (Worker `dossardpei-api`, KV `dossardpei-messages` en UE, routes, connexion, messages). Les stats (étape 2) ne sont pas encore branchées.

L'adresse de la page est **https://dossardpei.re/admin/**.
- La page est protégée par **un mot de passe** que tu choisis. Une fois entré, tu restes connecté 30 jours sur l'appareil. Après 5 erreurs, les essais sont bloqués pendant 1 heure.
- Les enregistrements passent par un petit **service Cloudflare (Worker)**. Il écrit dans le dépôt GitHub avec une clé limitée à ce dépôt.
- Les clés ne sont jamais dans le code. Ce sont des « secrets » du Worker, que tu saisis toi-même.

Il y a deux étapes. La première est indispensable, la seconde ajoute les statistiques.

---

## Étape 1 : l'admin (environ 15 minutes)

### 1. La clé GitHub
1. Sur github.com, clique sur ta photo, puis **Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token**.
2. Remplis les champs :
   - **Nom** : `Admin Dossard Péi`.
   - **Expiration** : 1 an. Note la date : il faudra la renouveler.
   - **Repository access** : *Only select repositories*, puis **Souweyd/dossard-pei**.
   - **Permissions › Repository permissions › Contents** : *Read and write*. Le reste ne change pas.
3. Clique sur **Generate token** et copie la clé (elle commence par `github_pat_`). Garde-la le temps de l'étape 3 et ne l'envoie à personne.

### 2. Le mot de passe
Choisis un mot de passe d'au moins **12 caractères**, que tu n'utilises nulle part ailleurs. Par exemple, quatre mots au hasard séparés par des tirets. Garde-le dans ton gestionnaire de mots de passe : tu le saisiras à l'étape 3 dans Cloudflare, et à chaque connexion (une fois par mois et par appareil). Ne l'envoie à personne.

### 3. Le service (Worker)
1. Dans Cloudflare, ouvre **Workers & Pages › Create › Worker** et choisis **Hello World**. Attention : il faut un **Worker**, pas un projet « Pages ».
2. Nomme-le `dossardpei-api`, puis clique sur **Deploy**.
3. Clique sur **Edit code**, efface tout, colle le contenu de `tools/admin-worker.js`, puis clique sur **Deploy**.
4. Va dans **Settings › Variables and Secrets** et ajoute ces variables :

| Nom | Type | Valeur |
|---|---|---|
| `REPO` | Text | `Souweyd/dossard-pei` |
| `BRANCH` | Text | `main` |
| `GITHUB_TOKEN` | **Secret** | la clé GitHub de l'étape 1 |
| `ADMIN_PASSWORD` | **Secret** | le mot de passe de l'étape 2 |

5. Va dans **Settings › Domains & Routes › Add › Route** et ajoute deux routes, toutes les deux sur la zone `dossardpei.re` :
   - `dossardpei.re/admin/api/*` (l'admin) ;
   - `dossardpei.re/api/form` (les formulaires du site).
6. **Espace des messages** :
   - dans **Storage & Databases › KV › Create**, crée un espace nommé `dossardpei-messages`, en juridiction **UE** ;
   - dans le Worker, ouvre **Settings › Bindings › Add › KV namespace** : nom de la variable `MSG`, espace `dossardpei-messages` ;
   - ajoute aussi le secret `SALT` : une suite de mots ou de caractères au hasard, que tu n'as pas besoin de retenir.
7. Ouvre https://dossardpei.re/admin/ et saisis ton mot de passe : l'admin s'ouvre.

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
- **Changer le mot de passe.** Modifie le secret `ADMIN_PASSWORD` dans le Worker. Toutes les sessions ouvertes sont alors déconnectées : c'est ce qu'il faut faire si tu penses qu'il a fuité.
- **En cas de souci.** Tu peux couper l'admin en supprimant la route `dossardpei.re/admin/api/*` du Worker. Le site public n'est pas touché.
- **Messages.** Les formulaires du site (contact, corrections, clubs) arrivent dans l'onglet **Messages**, et plus par e-mail. La pastille rouge donne le nombre de messages à traiter. Si l'espace des messages ne répond pas, le site les envoie par e-mail comme avant : rien ne se perd.
- **Logos des clubs.** Ils ne se changent pas dans l'admin (ils sont sur une planche commune) : il faut me les envoyer.
