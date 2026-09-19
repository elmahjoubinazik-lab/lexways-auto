# LEXWAYS — publication automatique de carrousels (Claude → Higgsfield → Zapier → Instagram)

Publie chaque jour ouvré un carrousel juridique **illustré** (mascotte 3D + objet + texte
exact) sur Instagram, **sans intervention humaine** et sans que ton ordinateur soit allumé.

## La chaîne, concrètement
1. **Claude** a écrit ce pipeline et une **banque de contenus pré-vérifiés** (`content_bank.json`).
2. **Higgsfield** a servi à générer, une fois, la bibliothèque d'illustrations (`assets/`).
   Elle est réutilisée chaque jour → pas de génération quotidienne (le hook API reste dispo
   dans `pipeline.py > higgsfield_generate` pour enrichir la biblio à la demande).
3. Le pipeline compose les slides, les **upload sur Cloudinary**, puis envoie l'e-mail
   « CARROUSEL LEXWAYS DU JOUR ».
4. **Zapier** (ton Zap Gmail→Instagram, inchangé) reçoit l'e-mail et **publie le carrousel**.

Le tout tourne dans une **GitHub Action planifiée** (cloud gratuit, avec accès internet).

## Mise en place (une seule fois)

1. **Crée un repo GitHub privé** et dépose ces fichiers dedans.
2. **Ajoute tes 34 visuels** dans le dossier `assets/` (les PNG Higgsfield + `nazik.jpg`).
   Les noms attendus sont dans `assets_map.json` (concept → nom de fichier). Adapte-les si besoin.
3. **Cloudinary** : crée un *upload preset* **non signé** (Settings → Upload).
4. **Gmail** : crée un **mot de passe d'application** (Compte Google → Sécurité → Mots de passe
   d'application) — 16 caractères. C'est lui qui envoie l'e-mail déclencheur.
5. Dans le repo : **Settings → Secrets and variables → Actions**, ajoute :
   - `CLOUDINARY_CLOUD` = `hyvzd1hy`
   - `CLOUDINARY_UPLOAD_PRESET` = le nom de ton preset (ex. `lexways_auto`)
   - `GMAIL_USER` = `elmahjoubinazik@gmail.com`
   - `GMAIL_APP_PASSWORD` = ton mot de passe d'application
   - `MAIL_TO` = `elmahjoubinazik@gmail.com`
6. **Teste** : onglet **Actions → LEXWAYS carrousel quotidien → Run workflow**. Vérifie le post.

## Le planning
`config.json` mappe chaque jour de la semaine à un carrousel de la banque.
Aujourd'hui : mardi = frontaliers, jeudi = travail, vendredi = immobilier.
Complète la banque (lundi = sociétés, mercredi = litiges…) au fil de l'eau.

## ⚠️ Déontologie — important
La publication est automatique, mais le **fond doit rester validé**. Ne laisse pas une IA
inventer du droit chaque jour : ce pipeline ne publie que des carrousels **écrits et
vérifiés à l'avance** dans `content_bank.json`. Ajoute un nouveau sujet uniquement après
avoir vérifié chaque référence sur les sources officielles (Fedlex, TF, admin.ch).

## Option validation en un clic
Si tu veux relire avant publication : change le cron en envoi vers TA boîte, relis, et
transfère l'e-mail toi-même. (Je peux te préparer cette variante.)

## Higgsfield API (optionnel)
Seulement pour générer de NOUVELLES illustrations (pas pour publier). Il faut activer
l'accès API dans la Console Higgsfield (e-mail pro + carte + solde), ajouter le secret
`HIGGSFIELD_API_KEY`, et compléter `higgsfield_generate()` selon docs.higgsfield.ai.
