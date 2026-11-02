# Politique de sécurisation du code — NOVA SERVICES

Version 1.0 — 15/10/2026 — Propriétaire : responsable sécurité applicative

## 1. Périmètre

Tous les dépôts de NOVA SERVICES : API Python, outil d'administration et scripts
d'automatisation.

## 2. Contrôles obligatoires

| Contrôle | Tous dépôts | Python uniquement | Local (pre-commit) | CI | Bloquant |
|---|:-:|:-:|:-:|:-:|:-:|
| Espaces / fin de fichier / YAML / fichiers volumineux | ✔ | | ✔ | ✔ | oui |
| detect-secrets (avec baseline) | ✔ | | ✔ | ✔ | oui |
| Bandit (sévérité ≥ Medium) | | ✔ | ✔ | ✔ | oui |
| Tests unitaires rapides (< 30 s) | | ✔ | ✔ | ✔ | oui |
| Suite de tests complète / intégration | | ✔ | | ✔ | oui (merge) |
| pip-audit | | ✔ | ✔ (*) | ✔ | oui en CI |
| Bandit toutes sévérités (rapport) | | ✔ | | ✔ | non, rapport |

(*) Localement, pip-audit dépend d'un service en ligne. S'il est indisponible,
le développeur peut commiter, mais la CI reste bloquante.

## 3. Conditions de blocage

- **Commit local** : un hook échoue → le commit est refusé.
- **Fusion vers `main`** : protection de branche côté serveur, c'est-à-dire pas de
  push direct, merge/pull request obligatoire, job CI `pre-commit` réussi et une
  approbation de revue au minimum. Les administrateurs ne sont pas exemptés.
- Le contournement local (`--no-verify`, `core.hooksPath`) est techniquement
  possible. C'est pour cette raison que la CI fait foi.
- **pre-commit.ci** (option, dépôts GitHub) : exécute les hooks sur chaque
  pull request, applique les corrections automatiques et propose les mises à
  jour des versions (`autoupdate`). Il complète la CI mais ne remplace ni la
  protection de branche, ni les tests applicatifs, ni la politique de gestion
  des vulnérabilités. Les hooks `language: system` (pytest, pip-audit) n'y
  tournent pas : ils restent dans le job CI du dépôt.

## 4. Traitement des faux positifs et exceptions

1. **Qualifier** avant tout : un résultat n'est déclaré faux positif qu'après
   vérification par le développeur **et** un relecteur.
2. **Vrai secret** : il ne va jamais dans le baseline. On le retire du code, on le
   révoque ou on le renouvelle s'il a été poussé, on nettoie l'historique si
   nécessaire et on ouvre un ticket incident.
3. **Faux positif detect-secrets** : on utilise `detect-secrets audit .secrets.baseline`
   (marquage `is_secret: false`) ou un `# pragma: allowlist secret` sur la ligne,
   accompagné d'un commentaire qui justifie l'exception. Les deux sont visibles en
   revue de code, puisque le baseline est versionné.
4. **Faux positif Bandit** : `# nosec BXXX` ciblé (jamais un `# nosec` nu) avec une
   justification.
5. **Dépendance vulnérable sans correctif** : on évalue l'exploitabilité dans notre
   contexte, puis on applique une mesure compensatoire (désactiver la fonction
   vulnérable, WAF, isolation) ou on remplace le paquet. L'exception passe par
   `pip-audit --ignore-vuln <ID>` dans la CI, avec ticket, date d'expiration
   (90 jours maximum) et réexamen.
6. **Validation** : toute exception est approuvée par le responsable sécurité
   applicative (ou son suppléant), tracée dans un ticket référencé dans le
   commit, puis réexaminée à expiration.

## 5. Preuve de correction

Une vulnérabilité est considérée comme corrigée quand :
- le commit de correction référence le ticket ;
- un test de non-régression reproduit le cas (exemple : `test_expression_injection_refused`) ;
- le contrôle qui l'avait détectée passe en CI sur ce commit ;
- l'entrée du baseline ou de l'exception correspondante a été supprimée.

## 6. Mise à jour des outils

- **Responsable** : le référent DevSecOps de chaque équipe.
- **Fréquence** : mensuelle, plus immédiate en cas d'alerte de sécurité sur un outil.
- **Procédure** : `pre-commit autoupdate` sur une branche dédiée, puis lecture des
  changelogs, `pre-commit run --all-files`, merge request relue et mise à jour
  de `requirements-dev.txt`.
- **Vérifier qu'un outil analyse réellement le code** : une mise à jour de Python
  peut casser un analyseur sans le faire échouer (voir RAPPORT.md, problème n°3).
  À chaque montée de version, on rejoue un fichier piège connu, par exemple
  contenant `eval()`, et on vérifie qu'il est détecté.
