# Rapport de TP — Sécuriser un dépôt Python avec pre-commit

Projet : NOVA SERVICES — US-DEVSEC-001

## 1. Analyse du code initial (section 3)

```python
import os

def get_message():
    password = "demo-secret-123"
    user_input = input("Entrez une expression : ")
    result = eval(user_input)
    return f"Résultat : {result}"
```

**Problèmes de qualité**
- `import os` est importé mais jamais utilisé.
- Une seule ligne vide entre l'import et la fonction (PEP 8 en demande deux).
- La variable `password` est assignée mais jamais utilisée (code mort).
- La fonction mélange saisie (`input`), calcul et formatage. Elle est donc impossible à tester unitairement sans simuler stdin.
- Aucun typage, aucune gestion d'erreur : une expression invalide lève une `SyntaxError` brute.

**Risques de sécurité**
- **Secret en dur** (CWE-798/259).
- **Injection de code via `eval()`** (CWE-95).

**Pourquoi `eval()` est dangereux.** `eval()` exécute n'importe quelle expression
Python avec les droits du processus. Une saisie comme
`__import__('os').system('rm -rf ~')` ou `open('/etc/passwd').read()` donne à
l'utilisateur une exécution de code arbitraire : lecture de fichiers, de
variables d'environnement (et donc des secrets), ouverture d'un shell, etc.
Restreindre `__builtins__` ne suffit pas, car il existe de nombreuses techniques
d'évasion via les attributs d'objets (`().__class__.__mro__…`).

**Pourquoi pas de mot de passe dans le code.** Le code source est copié partout
(postes, forks, CI, sauvegardes, artefacts). Un secret commité reste dans
l'historique Git même après suppression. Il est partagé avec tous ceux qui ont
accès en lecture, ne peut pas varier selon l'environnement (dev/prod) et ne peut
pas être renouvelé sans redéploiement.

**Correction proposée.** Lire le secret depuis l'environnement (`os.getenv`) et
remplacer `eval()` par une liste blanche d'opérations (`calculate()`), ce qui
donne le code actuel de `app.py`.

## 2. Problèmes détectés et corrections (livrable d'analyse)

### Problème 1 — Injection de code via `eval()` (Bandit B307, Medium/High)
- **Détection** : `bandit` → `B307:blacklist Use of possibly insecure function`, `app.py:6`.
- **Correction** : `eval()` supprimé, remplacé par `calculate(a, b, operation)`
  avec quatre opérations autorisées et un `ValueError` pour toute autre valeur.
- **Preuve** : `test_unknown_operation` et `test_expression_injection_refused`
  vérifient qu'une opération non prévue (y compris une charge
  `__import__('os')…`) est refusée. Bandit passe sur la version corrigée.

### Problème 2 — Mot de passe en dur (detect-secrets « Secret Keyword »)
- **Détection** : le premier commit est **refusé** par detect-secrets
  (`Secret Type: Secret Keyword, Location: app.py:4`).
- **Point notable** : Bandit voit aussi ce problème (B105), mais en sévérité
  **Low**. Avec l'option `-ll` du TP, le hook Bandit **ne le signale pas**. Seule
  la combinaison des deux outils couvre ce cas.
- **Correction** : secret déplacé dans `.env` (ignoré par Git), `.env.example`
  vide versionné, lecture par `get_password()` qui échoue explicitement si la
  variable est absente et n'affiche jamais la valeur.
- **Le baseline n'a pas été utilisé pour masquer ce résultat**. Il a été régénéré
  *après* correction et ne contient aucune entrée. La seule exception est un
  `pragma: allowlist secret` sur une valeur de test fictive dans `test_app.py`,
  visible en revue de code.

### Problème 3 — Faux négatif silencieux : Bandit 1.8.6 incompatible avec Python 3.14
- **Constat** : avec la version épinglée dans l'énoncé (`rev: 1.8.6`), le hook
  Bandit affichait **`Passed`** alors que `eval()` était présent.
  En mode verbeux : `ERROR Exception occurred when executing tests against ./app.py`
  et `Files skipped (1): ./app.py (exception while scanning file)`. Bandit plante
  sur l'AST de Python 3.14, ignore le fichier et retourne quand même le code 0.
- **Correction** : `rev` passé à `1.9.4`. Bandit détecte alors bien B307 et bloque.
- **Leçon** : un contrôle vert ne prouve pas que l'analyse a eu lieu. Il faut
  vérifier les outils à chaque montée de version, avec un fichier piège (voir
  POLITIQUE.md §6).

### Observation — baseline vide au premier `detect-secrets scan`
`detect-secrets scan` n'analyse que les fichiers **suivis par Git**. Lancé avant
le premier `git add`, il produit un baseline vide. C'est sans conséquence ici,
mais dans un dépôt existant, l'ordre des opérations change ce qui entre dans le
baseline.

## 3. Scénarios de validation (section 8) — résultats obtenus

| Scénario | Hook déclenché | Résultat |
|---|---|---|
| Espaces en fin de ligne (`ws.py`) | trailing-whitespace | Échec + fichier corrigé (`Fixing ws.py`), commit refusé |
| Secret suspect (`API_KEY = "AKIA…EXAMPLE"`) | detect-secrets | Échec : *AWS Access Key* + *Secret Keyword*, commit refusé |
| Fonction risquée (`subprocess.run(..., shell=True)`) | bandit | Échec : B602, commit refusé |
| Test modifié pour échouer | pytest | Échec : `assert 5 == 6`, commit refusé |
| `requests==2.19.0` ajouté | pip-audit | Échec : 37 vulnérabilités (requests, idna, urllib3), commit refusé |
| Modification saine | tous | Commit créé |
| `git -c core.hooksPath=/dev/null commit` avec un `eval()` | aucun | **Commit créé sans contrôle** → d'où la CI et la protection de branche |

Exemple de lecture d'un résultat pip-audit (scénario 5) :

| Paquet | Version | Identifiant | Version corrigée | Impact | Action |
|---|---|---|---|---|---|
| requests | 2.19.0 | PYSEC-2018-28 (CVE-2018-18074) | 2.20.0 | Fuite de l'en-tête `Authorization` lors d'une redirection HTTPS→HTTP | Monter à la dernière 2.x |
| urllib3 | 1.23 | PYSEC-2019-132 (CVE-2019-11236) | 1.24.3 | Injection CRLF si le paramètre de requête est contrôlé par l'attaquant | Résolu par la montée de requests |

Exécution complète sur la version finale : voir `resultats-controles.txt`.

## 4. Indicateurs de suivi

| Indicateur | Source | Propriétaire | Fréquence | Seuil d'alerte | Action déclenchée |
|---|---|---|---|---|---|
| **Taux de dépôts configurés** (dépôts avec `.pre-commit-config.yaml` + job CI / dépôts concernés) | API GitLab/GitHub (présence des fichiers) | Responsable sécurité | Mensuelle | < 90 % | Relance des équipes, accompagnement à la mise en place |
| **Délai médian de correction** (détection en CI → pipeline vert sur le correctif) | Tickets + historique CI | Lead dev de chaque équipe | Mensuelle | > 7 jours (critique/haute) | Revue en comité, priorisation au sprint suivant |
| **Nombre d'exceptions actives** (entrées `is_secret: false`, `# nosec`, `--ignore-vuln`) | Grep sur les dépôts + registre des exceptions | Responsable sécurité | Mensuelle | Exception expirée, ou hausse > 20 % | Réexamen, suppression ou renouvellement justifié |

En complément : le taux de pipelines CI réussis (s'il est bas, les contrôles
locaux sont contournés ou non installés) et le nombre de vulnérabilités de
dépendances ouvertes après qualification.

Une hausse des détections peut refléter une meilleure couverture plutôt qu'une
dégradation : ces indicateurs se lisent avec le nombre de dépôts couverts.

## 5. Exercice complémentaire (section 10)

1. **Contrôles communs à tous les dépôts** : hooks génériques (espaces, fin de
   fichier, YAML, gros fichiers, `check-merge-conflict`, `detect-private-key`) et
   detect-secrets.
2. **Contrôles spécifiques Python** : Bandit, pytest, pip-audit, éventuellement
   un linter/formateur (ruff).
3. **Bloquants avant commit** : tout ce qui est rapide et déterministe, c'est-à-dire
   hooks génériques, detect-secrets (un secret commité est déjà une fuite),
   Bandit et tests rapides.
4. **CI uniquement** : suite de tests complète, pip-audit (dépend du réseau et
   d'une base externe qui évolue), Bandit toutes sévérités, scan de conteneurs,
   SAST plus lourd.
5. **Éviter qu'une exception masque un vrai secret** : baseline versionné et
   relu en merge request, `detect-secrets audit` obligatoire, pragmas ciblés
   ligne par ligne, CODEOWNERS sécurité sur `.secrets.baseline`, interdiction de
   régénérer le baseline sans revue.
6. **Mise à jour des versions des hooks** : le référent DevSecOps de chaque
   équipe, de façon mensuelle et contrôlée (`pre-commit autoupdate` + MR).
7. **Prouver la correction d'une vulnérabilité** : commit lié au ticket, test de
   non-régression, pipeline CI vert sur ce commit, exception retirée.
8. **Dépendance vulnérable sans correctif** : évaluer l'exploitabilité
   (le code appelle-t-il la fonction vulnérable ?), appliquer une mesure
   compensatoire ou remplacer le paquet, puis exception tracée
   (`--ignore-vuln`), datée, approuvée et réexaminée à échéance.

## 6. Questions de compréhension (section 13)

1. **Hook pre-commit** : script exécuté par Git juste avant la création d'un
   commit. Un code retour non nul annule le commit. Le framework *pre-commit*
   gère ces scripts de façon déclarative et versionnée.
2. **Local vs CI** : le contrôle local donne un retour immédiat au développeur
   mais reste facultatif et contournable. Le contrôle CI tourne dans un
   environnement maîtrisé, s'applique à tous et peut conditionner le merge.
3. **Versionner `.pre-commit-config.yaml`** : mêmes règles et mêmes versions pour
   toute l'équipe et pour la CI, changements relus et historisés.
4. **Faux positifs de detect-secrets** : l'outil repose sur des heuristiques
   (motifs, mots-clés comme `password`, entropie) sans connaître le contexte.
   Une valeur fictive ou un hash peut donc ressembler à un secret.
5. **Le baseline n'est pas une cachette** : un secret listé dans le baseline
   n'est plus signalé, mais il reste exploitable dans le code et l'historique. Le
   baseline sert à suivre des faux positifs audités, pas à accepter un risque.
6. **`eval()` sur une entrée non fiable** : exécution de code arbitraire avec
   les droits de l'application.
7. **Exclure `.env`** : il contient les vraies valeurs locales. Commité, il
   expose les secrets à tous les lecteurs du dépôt, et ce durablement via
   l'historique.
8. **Variable d'environnement ≠ gestion de secret** : elle reste en clair
   (lisible via `/proc/<pid>/environ`, dumps, logs de crash, processus enfants),
   sans rotation, sans contrôle d'accès fin ni audit. En production, il faut un
   coffre (Vault, gestionnaire du cloud).
9. **Analyse de code vs audit de dépendances** : la SAST (Bandit) examine *notre*
   code pour y trouver de mauvaises pratiques. L'audit (pip-audit) compare les
   *paquets tiers et leurs versions* à des bases de vulnérabilités connues.
10. **Tests en CI malgré le hook** : le hook peut être absent, désactivé ou
    contourné (démontré au scénario 7). La CI est le point de contrôle commun et
    non contournable.
11. **Empêcher les pushes directs sur `main`** : protection de branche ou règle
    de dépôt côté serveur (GitLab *Protected branches*, GitHub *Rulesets*), avec
    push interdit, MR/PR obligatoire, CI verte requise, approbation requise, sans
    exemption pour les administrateurs.
12. **Indicateurs** : voir la section 4.
