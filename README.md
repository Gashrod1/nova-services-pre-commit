# NOVA SERVICES — dépôt sécurisé par pre-commit

Mise en œuvre de l'US-DEVSEC-001 : contrôles de qualité et de sécurité exécutés
automatiquement avant chaque commit, puis rejoués en CI.

## Environnement de référence

| Outil          | Version |
|----------------|---------|
| Python         | 3.14    |
| pre-commit     | 4.7.0   |
| bandit         | 1.9.4   |
| detect-secrets | 1.5.0   |
| pytest         | 9.1.1   |
| pip-audit      | 2.10.1  |

Les versions sont épinglées dans `requirements-dev.txt` et `.pre-commit-config.yaml`.

## Installation (à faire une fois par poste)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows : .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cp .env.example .env                 # puis renseigner APP_PASSWORD localement
pre-commit install
```

Les hooks `pytest` et `pip-audit` sont de type `language: system` : le
virtualenv doit être **activé** au moment du commit.

## Utilisation

```bash
pre-commit run --all-files     # tous les contrôles sur tout le dépôt
pytest -q                      # tests unitaires seuls
pip-audit -r requirements.txt  # audit des dépendances seul
```

Si un hook modifie un fichier (espaces, fin de fichier), relire avec `git diff`,
refaire `git add`, puis recommencer le commit.

## Contrôles en place

| Hook                    | Rôle                                         | Bloquant |
|-------------------------|----------------------------------------------|----------|
| trailing-whitespace     | Supprime les espaces en fin de ligne          | oui (corrige) |
| end-of-file-fixer       | Normalise la fin de fichier                   | oui (corrige) |
| check-added-large-files | Refuse les fichiers > 500 Ko                  | oui |
| check-yaml              | Vérifie la syntaxe YAML                       | oui |
| bandit (`-ll`)          | Analyse statique Python, sévérité ≥ Medium    | oui |
| detect-secrets          | Détection de secrets (baseline `.secrets.baseline`) | oui |
| pytest                  | Tests unitaires                               | oui |
| pip-audit               | Vulnérabilités connues des dépendances        | oui |

La CI (`.github/workflows/security.yml` ou `.gitlab-ci.yml`) rejoue
`pre-commit run --all-files` sur chaque merge/pull request et sur `main`.

Voir aussi : [`POLITIQUE.md`](POLITIQUE.md) et [`RAPPORT.md`](RAPPORT.md).
