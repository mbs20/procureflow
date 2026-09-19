# Stabilisation v0.1.1 — état du 18 septembre 2026

**READY FOR MANUAL QA** — toutes les gates automatisées demandées sont validées.

Base : `1548b5695f844e3e38a73d64c0a13324983fb5a0`.
Branche : `fix/v0.1.1-stabilization`. Publication autorisée après les gates vertes ; aucun merge ni tag.
Le SHA final des commits locaux est donné dans la réponse de livraison.

## Corrections et preuves

Les identifiants ci-dessous reprennent les anomalies de l’audit, reproduites par code, tests API et Playwright automatisé. Aucune navigation manuelle.

| ID | Cause et correction | Validation |
|---|---|---|
| B1 | Pas HTML .05 incompatible avec minimum .01 : pas .01 pour les pondérations. | Soumission native du preset Balanced dans Chromium. |
| B2 | Décimaux sérialisés en chaînes et conversions permissives : validation numérique stricte, motif obligatoire, zéro préservé. | 14 tests numériques et 5 scénarios formulaires. |
| B3 | Module PDF .mjs mal typé par nginx : type JavaScript explicite, conservation de nosniff. | Test de configuration ; HTTP nginx et canvas PDF Chromium validés. |
| B4–B5 | Contrat UI différent de config_payload/results_payload : adaptateurs, prérequis explicites, erreurs structurées et fin du chargement. | 6 tests de contrat et 6 états scoring dans Chromium. |
| B6 | Offres needs_review incluses : matrice limitée aux extractions courantes approuvées. | Tests matrice de confiance. |
| B7 | Création avant upload : endpoint atomique, rollback et nettoyage du fichier sur échec. | 9 régressions ingestion, dont taille, écriture partielle, commit échoué et retry. |
| B8 | Nombres libres pris pour des lignes : rejet des métadonnées/dimensions, lecture de cellules sous en-tête explicite, confiance prudente et avertissement. | PDF natif structuré, PDF générique et preuves inconnues testés. |
| B9 | GET sur route d’upload : téléchargement du document identifié ; repli vers revue si ambigu. | Contrat source côté backend ; navigation navigateur 200 vers le document exact validée. |
| B10 | URI data et CSV sans échappement : Blob, échappement des cellules et neutralisation des formules textuelles. | Test CSV Unicode, guillemets, retours ligne, formules et nombres. |
| B11 | Résumé calculé avant override : délai effectif agrégé, original conservé, cellule du tiroir actualisée après rafraîchissement. | Régression matrice sur délai effectif et provenance. |
| B12 | Ancien run incomplet accepté : validation identité, cohorte, compteurs et hashes avant DecisionContext. | Tests narratifs et parcours complet extraction → approbation → snapshot → scoring → contexte → narration → attribution. |
| B13 | Page placeholder : liste réelle paginée des événements, sans divulgation de l’ancien actor_id contenant parfois une clé. | API et deux scénarios Chromium EN/FR. |
| B14 | Affichage du dernier award seulement : affichage de toute la liste retournée. | Suite décisions existante ; révocation/réattribution live validée. |
| B15 | Sidebar fixe : navigation mobile horizontale et contenu pleine largeur ; contraste des boutons corrigé. | 390 px sans débordement et contrôle axe WCAG. |
| B16 | DNS backend figé : resolver Docker et proxy variable nginx. | Test statique ; recréation backend et reconnexion sans restart frontend validées. |
| Worker | Healthcheck HTTP hérité : ping Celery ciblé sur ce worker. | Test statique ; sonde broker ciblée et état healthy validés. |

## Gates exécutées

- Backend : `python -m pytest -q --tb=short` : **151 passed**, 5 avertissements de dépréciation.
- Backend : `ruff check` sur tous les fichiers Python modifiés/ajoutés : **passed**.
- Frontend : `npm run typecheck` : **passed**.
- Frontend : `npm test -- --run` : **51 passed**.
- Frontend : `npm run build` : **passed** ; avertissement de taille du bundle existant.
- Frontend : `npx playwright test --grep-invert 'Docker|docker' --reporter=line` : **35 passed**.
- Frontend : `npx playwright test e2e/stabilization_audit.spec.ts --reporter=line` : **2 passed**.
- Contrat OpenAPI régénéré, test de cohérence inclus dans pytest.
- `git diff --check` : aucun défaut d’espacement.

Les anciens tests scoring/décision appelaient une route d’approbation disparue sans vérifier sa réponse. Ils utilisent désormais PATCH /status et passent avec la règle approved-only. Tests Windows isolés dans un répertoire temporaire ; aucune base réelle réinitialisée.

## Validation runtime finale

SHA de départ de cette reprise : `e89db8f0c01e3c3a2ca047afdd5abc870f8eaaec`.
Commit du code runtime validé : `4b658ac858f3f5eb8c93eddd77a4a0868ef4b5ad`.
Le commit documentaire suivant ne change pas le code testé ; le SHA final de branche est fourni dans le rapport de livraison.

| Contrôle | Résultat final |
|---|---|
| `docker compose --profile demo up --build -d` | Réussi, sans suppression de volumes. |
| postgres / redis / backend / frontend / worker | Tous healthy. |
| seed-demo | Exited (0), terminaison attendue du job. |
| Worker Celery | Ping ciblé : pong. Cinq sondes successives réussies, FailingStreak 0. |
| Backend health | healthy ; base et Redis healthy ; Celery configured_distributed. |
| Journaux | Aucun ERROR/Traceback dans les 100 dernières lignes backend/worker inspectées. |
| Alembic PostgreSQL réel | `2231598cc1bc (head)` ; check : aucune nouvelle opération. |
| Préservation données | Les 72 identifiants RFQ relevés avant recréation sont tous présents après. Aucun reset. |
| PDF.js production | HTTP 200, application/javascript, nosniff, 1 366 356 octets ; canvas natif rendu dans Chromium. |
| DNS nginx | Backend seul recréé ; identité frontend inchangée ; proxy HTTP 200 et backend healthy sans restart frontend. |
| CSV | Téléchargement réel non vide ; Unicode, virgules, guillemets, nouvelle ligne et formule neutralisée validés. |
| Document source | Quotation/document exacts ; signature %PDF-, navigation navigateur HTTP 200 application/pdf, aucun 405. |
| Historique awards | Confirmé → révoqué avec motif → nouveau draft → confirmé. Deux awards, événements antérieurs intacts, motifs visibles. |
| pytest Docker | 150 passed, 1 skipped : docs/OpenAPI non monté dans le conteneur. |
| OpenAPI hôte | 1 passed, couvre le test ignoré dans Docker. |
| Frontend | typecheck OK, 51 tests passed, build OK. Test runtimeConfig relancé après modification sonde : 2 passed. |
| Playwright complet | **41 passed (52.0s), aucun skip**, dont les quatre suites docker_live. |
| EN/FR et responsive | Tests langue/persistance/journal et mobile 390 px réussis ; contrôles axe des suites réussis. |
| Git | Diff revu et diff --check sans erreur ; fichiers temporaires/logs hors commit. |

Les parcours applicatifs sont servis par nginx Docker sur 5173. Seules les fixtures de composants de formulaires utilisent Vite sur 5174, afin de ne pas substituer le serveur dev au frontend de production. Le nouveau scénario runtime exige explicitement un serveur nginx.

Trois défauts/ajustements runtime ont été traités : lecture de `award_justification` dans l’historique, libellé EN/FR cohérent du lien document, et sonde Celery sans import des extracteurs. La sonde conserve un ping ciblé avec timeout broker de 5 s ; timeout conteneur 30 s et grâce de démarrage 60 s évitent les faux négatifs observés sous charge. Les anciens tests live utilisent désormais la route PATCH /status ; le PDF vérifie la réponse de navigation, car l’URL du lecteur intégré Chromium est opaque.

Aucune anomalie bloquante restante dans les contrôles demandés. Avertissements connus non bloquants : dépréciations Python/Starlette et taille du bundle frontend. Les tests créent des données synthétiques conservées ; aucune donnée ancienne supprimée. Cette validation autorise la QA manuelle, pas une release.

READY FOR MANUAL QA
