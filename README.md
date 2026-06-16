# LBC PC Analyzer

Extension Chrome + API Cloudflare Worker pour analyser les annonces Leboncoin de PC fixes, mini-PC et configurations avec GPU dedie.

L'extension lit les annonces visibles, l'API extrait les composants avec des regex et des tables CPU/GPU locales, puis calcule un score de rentabilite sur 100. Aucune IA n'est utilisee en V1 : le scoring repose sur des regles, des benchmarks locaux et un auto-apprentissage prudent via D1.

## Fonctionnalites

- Extension Chrome Manifest V3 injectee sur `leboncoin.fr`.
- Analyse automatique sur les pages annonce ordinateur/informatique.
- Badges de score discrets sur les pages de recherche, avec tooltip au survol.
- Encart detaille sur les pages annonce : marque, modele, CPU, annee CPU, GPU, RAM, stockage, prix, score, verdict et raison.
- Couleurs rapides sur les scores et composants pour reperer vite les bons/mauvais points.
- Historique local des 20 dernieres analyses.
- Favoris stockes dans `chrome.storage.local`.
- API publique Cloudflare Worker sur `https://pc-analyzer-api.plaw.fr`.
- D1 pour stocker les observations et les regles apprises.
- Backend FastAPI local conserve pour le dev/test sur `http://localhost:8000`.
- Scoring sans IA : regex + tables CPU/GPU locales + regles apprises.

## Architecture

```text
backend/
  app/
    main.py       API FastAPI locale de dev
    parser.py     extraction marque, modele, CPU, RAM, stockage, prix
    scoring.py    tables fallback, annee CPU et calcul du score
    learning.py   collecte locale SQLite et suggestions d'amelioration
    cpu_benchmarks.json
    gpu_benchmarks.json
  tests/
    test_parser.py
    test_learning.py
extension/
  manifest.json
  content.js
  styles.css
worker/
  src/index.ts    API publique Cloudflare Worker
  migrations/     schema D1 observations + auto-apprentissage
  wrangler.toml   domaine custom et cron toutes les 5 minutes
.github/workflows/
  deploy-api.yml  CI/CD Worker au push sur main
```

Architecture en production :

```text
Leboncoin -> Extension Chrome -> https://pc-analyzer-api.plaw.fr -> Cloudflare Worker -> D1
```

Architecture locale de dev :

```text
Leboncoin -> Extension Chrome -> http://localhost:8000 -> FastAPI -> SQLite locale
```

## Installation Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verifier que le backend tourne :

```bash
curl http://localhost:8000/health
```

Analyser une annonce en ligne de commande :

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"title":"Beelink SER5 Ryzen 7 5700U 16Go 512Go SSD","price":280,"description":"Mini PC avec NVMe 512 Go"}'
```

## Installation Extension Chrome

1. Ouvrir `chrome://extensions`.
2. Activer le mode developpeur.
3. Cliquer sur **Charger l'extension non empaquetee**.
4. Selectionner le dossier `extension`.
5. Ouvrir une recherche ou une annonce Leboncoin.

Par defaut, l'extension utilise l'API publique :

```text
https://pc-analyzer-api.plaw.fr
```

Pour basculer temporairement sur l'API FastAPI locale :

```js
chrome.storage.local.set({ lbcmp_api_base: "http://localhost:8000" })
```

Ensuite recharge l'extension et la page Leboncoin.

Sur une page de recherche, les annonces detectees recoivent un badge `score/100`.
Sur une page annonce, un encart complet apparait a droite.

## Scoring

Le score combine :

- CPU : 50 %
- RAM : 20 %
- stockage : 10 %
- prix : 20 %

Des ajustements sont appliques :

- penalite pour CPU faibles ou anciens comme `N100`, `N150`, `N4000`, `G630`, `A10`, certains i5/i3 anciens ;
- bonus pour certaines marques fiables ;
- bonus pour RAM >= 32 Go ;
- bonus pour SSD >= 512 Go.

Les regex sont dans `backend/app/parser.py` et `worker/src/index.ts`. Le scoring utilise en priorite les bases benchmark CPU/GPU, puis les regles apprises, puis les tables de fallback.

Le detail renvoye par `/analyze` expose notamment :

- `details.cpu_score` et `details.gpu_score` ;
- `details.cpu_year` ;
- `details.ram_score`, `details.storage_score`, `details.price_score` ;
- `details.scoring_profile` : `compact_pc` ou `desktop_gpu`.

### Base CPU benchmark

`backend/app/cpu_benchmarks.json` contient une base locale inspiree d'un scoring type PassMark CPU Mark :

```json
{
  "Ryzen 7 5800U": {
    "cpu_mark": 18800,
    "single_thread": 3050,
    "score": 79,
    "tier": "good"
  }
}
```

Le champ `score` est prioritaire. S'il est absent, le backend estime `cpu_mark / 240`, plafonne a 100.

## Apprentissage Local

Le backend enregistre automatiquement les analyses dans :

```text
backend/data/learning.sqlite
```

Cette base sert a detecter les trous du parser et du scoring. Elle reste locale et n'est pas versionnee.

Endpoints utiles :

```bash
curl http://localhost:8000/learning/stats
curl "http://localhost:8000/learning/examples?flag=missing_cpu&limit=20"
curl "http://localhost:8000/learning/examples?flag=missing_storage&limit=20"
curl "http://localhost:8000/learning/suggestions?limit=30"
```

Flags principaux :

- `missing_cpu` : CPU non detecte.
- `unknown_cpu_score` : CPU detecte mais absent de la table de scoring.
- `missing_ram` : RAM non detectee.
- `missing_storage` : stockage non detecte.
- `missing_brand` : marque non detectee.
- `low_score_good_cpu` : score bas malgre un CPU correct.

Boucle d'amelioration :

1. Naviguer sur Leboncoin avec le backend lance.
2. Consulter `/learning/stats` pour voir les problemes frequents.
3. Consulter `/learning/suggestions` pour obtenir les candidats CPU, marques et formats stockage.
4. Ajouter les candidats valides dans `parser.py` et `scoring.py`.
5. Lancer les tests.

Le backend lance aussi un auto-apprentissage prudent toutes les 5 minutes. Il ne modifie pas les fichiers Python : il ajoute des regles runtime dans SQLite quand un candidat revient assez souvent.

Endpoints auto-apprentissage :

```bash
curl -X POST http://localhost:8000/learning/auto-run
curl http://localhost:8000/learning/rules
```

Les regles apprises sont appliquees automatiquement a `/analyze` tant que le backend utilise la meme base SQLite locale.

## Tests

```bash
cd backend
python3 -m pytest
```

## Limites

- Pas d'IA en V1.
- Les selecteurs Leboncoin peuvent changer.
- Les badges de recherche dependent de la structure HTML courante des cartes.
- Les suggestions d'apprentissage doivent etre validees avant integration.


## PC fixes et GPU

La logique couvre aussi les PC fixes non portables :

- extraction GPU dedie : RTX, GTX, Radeon RX, Radeon 780M, Intel Arc ;
- extraction RAM avancee : DDR3/DDR4/DDR5 et frequence MHz ;
- extraction stockage : NVMe, M.2, SATA SSD, HDD, eMMC ;
- profil de scoring `desktop_gpu` quand un GPU dedie est detecte.

Base GPU benchmark :

```text
backend/app/gpu_benchmarks.json
```

Quand un GPU dedie est detecte, le scoring utilise environ :

- CPU : 35 %
- GPU : 30 %
- RAM : 15 %
- stockage : 10 %
- prix : 10 %

Sans GPU dedie, le profil PC compact reste utilise.


## GPU et VideoCardBenchmark

Le scoring GPU suit la meme idee que la base CPU : une table locale inspiree de scores type PassMark / VideoCardBenchmark.

Source de reference : `https://www.videocardbenchmark.net/`, qui publie des benchmarks GPU PassMark G3D issus de PerformanceTest.

Fichier local :

```text
backend/app/gpu_benchmarks.json
```

L'auto-apprentissage fonctionne aussi pour les GPU :

- les annonces alimentees par l'extension sont stockees dans SQLite ;
- `/learning/suggestions` remonte aussi `gpu_candidates` ;
- toutes les 5 minutes, les GPU candidats frequents sont appris dans `learned_gpu` ;
- `/analyze` applique les GPU appris au runtime, sans modifier les fichiers Python.

## Marques

Le scoring applique maintenant un ajustement par marque :

- bonus fort : Lenovo, HP, Dell, Shuttle ;
- bonus PC compact : Minisforum, Beelink, Geekom ;
- bonus leger : GMKtec, MSI, Asus, Intel ;
- malus leger : Chuwi, NiPoGi, Acemagic.

Le detail est visible dans `details.brand_adjustment` et dans les raisons du score.


## API Cloudflare Worker + D1

L'API principale est hebergee dans `worker/` pour permettre une extension utilisable sans backend local.

Par defaut, l'extension utilise l'API Cloudflare publique :

```text
https://pc-analyzer-api.plaw.fr
```

Commandes :

```bash
cd worker
npm install
wrangler d1 migrations apply lbc_pc --remote
wrangler deploy
```

Endpoints Worker :

- `GET /health`
- `POST /analyze`
- `GET /learning/stats`
- `GET /learning/examples`
- `GET /learning/rules`

D1 contient :

- `observations`
- `learned_cpu`
- `learned_gpu`
- `learned_brand`

Avant le premier deploy public, le compte Cloudflare doit avoir un sous-domaine `workers.dev` actif, ou un route/custom domain configure dans `wrangler.toml`.




## Auto-apprentissage Cloudflare

Le Worker execute un cron toutes les 5 minutes (`*/5 * * * *`). Il lit les observations D1 recentes, detecte les CPU/GPU/marques frequents qui manquent ou tombent en score inconnu, puis alimente :

- `learned_cpu` ;
- `learned_gpu` ;
- `learned_brand`.

Declenchement manuel possible :

```bash
curl https://pc-analyzer-api.plaw.fr/learning/auto-run
curl https://pc-analyzer-api.plaw.fr/learning/rules
```

L'API applique ensuite ces regles apprises avant de scorer une annonce.

## CI/CD API Cloudflare

Le workflow GitHub Actions `.github/workflows/deploy-api.yml` teste et deploie automatiquement le Worker quand `worker/**` change sur `main`.

Secrets GitHub requis dans `Settings > Secrets and variables > Actions` :

- `CLOUDFLARE_API_TOKEN` : token Cloudflare avec droit de deploy Worker et acces D1 ;
- `CLOUDFLARE_ACCOUNT_ID` : identifiant du compte Cloudflare.

Le deploiement cible le domaine custom configure dans `worker/wrangler.toml` :

```text
pc-analyzer-api.plaw.fr
```
