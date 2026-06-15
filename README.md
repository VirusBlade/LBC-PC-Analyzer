# LBC Mini-PC Analyzer

Extension Chrome + backend FastAPI pour analyser localement les annonces Leboncoin de mini-PC et PC fixes.

L'extension lit les annonces visibles, le backend extrait les composants avec des regex et une table CPU locale, puis calcule un score de rentabilite sur 100. Aucune IA externe n'est utilisee et rien n'est envoye hors de ta machine.

## Fonctionnalites

- Extension Chrome Manifest V3 injectee sur `leboncoin.fr`.
- Analyse automatique sur les pages annonce ordinateur/informatique.
- Badges de score discrets sur les pages de recherche, avec tooltip au survol.
- Encart detaille sur les pages annonce : marque, modele, CPU, GPU, RAM, stockage, score, verdict et raison.
- Historique local des 20 dernieres analyses.
- Favoris stockes dans `chrome.storage.local`.
- Backend local FastAPI sur `http://localhost:8000`.
- Scoring sans IA : regex + table CPU locale.
- Apprentissage local SQLite pour reperer les CPU, marques et formats non reconnus.

## Architecture

```text
backend/
  app/
    main.py       API FastAPI
    parser.py     extraction marque, modele, CPU, RAM, stockage, prix
    scoring.py    table CPU et calcul du score
    learning.py   collecte locale et suggestions d'amelioration
  tests/
    test_parser.py
    test_learning.py
extension/
  manifest.json
  content.js
  styles.css
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
5. Demarrer le backend sur `http://localhost:8000`.
6. Ouvrir une recherche ou une annonce Leboncoin.

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

Les regex sont dans `backend/app/parser.py`. Le scoring utilise en priorite `backend/app/cpu_benchmarks.json`, puis les regles apprises SQLite, puis la table de fallback dans `backend/app/scoring.py`.

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

Sans GPU dedie, le profil mini-PC reste utilise.
