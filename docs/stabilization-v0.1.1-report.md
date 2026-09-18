# Stabilisation v0.1.1 — état du 18 septembre 2026

**NOT READY FOR MANUAL QA** — validations Docker et migrations encore bloquées.

Base : `1548b5695f844e3e38a73d64c0a13324983fb5a0`.
Branche : `fix/v0.1.1-stabilization`. Aucun push, merge ou tag.
Le SHA final des commits locaux est donné dans la réponse de livraison.

## Corrections et preuves

Les identifiants ci-dessous reprennent les anomalies de l’audit, reproduites par code, tests API et Playwright automatisé. Aucune navigation manuelle.

| ID | Cause et correction | Validation |
|---|---|---|
| B1 | Pas HTML .05 incompatible avec minimum .01 : pas .01 pour les pondérations. | Soumission native du preset Balanced dans Chromium. |
| B2 | Décimaux sérialisés en chaînes et conversions permissives : validation numérique stricte, motif obligatoire, zéro préservé. | 14 tests numériques et 5 scénarios formulaires. |
| B3 | Module PDF .mjs mal typé par nginx : type JavaScript explicite, conservation de nosniff. | Test de configuration ; validation HTTP Docker restante. |
| B4–B5 | Contrat UI différent de config_payload/results_payload : adaptateurs, prérequis explicites, erreurs structurées et fin du chargement. | 6 tests de contrat et 6 états scoring dans Chromium. |
| B6 | Offres needs_review incluses : matrice limitée aux extractions courantes approuvées. | Tests matrice de confiance. |
| B7 | Création avant upload : endpoint atomique, rollback et nettoyage du fichier sur échec. | 9 régressions ingestion, dont taille, écriture partielle, commit échoué et retry. |
| B8 | Nombres libres pris pour des lignes : rejet des métadonnées/dimensions, lecture de cellules sous en-tête explicite, confiance prudente et avertissement. | PDF natif structuré, PDF générique et preuves inconnues testés. |
| B9 | GET sur route d’upload : téléchargement du document identifié ; repli vers revue si ambigu. | Contrat source côté backend ; téléchargement navigateur à confirmer. |
| B10 | URI data et CSV sans échappement : Blob, échappement des cellules et neutralisation des formules textuelles. | Test CSV Unicode, guillemets, retours ligne, formules et nombres. |
| B11 | Résumé calculé avant override : délai effectif agrégé, original conservé, cellule du tiroir actualisée après rafraîchissement. | Régression matrice sur délai effectif et provenance. |
| B12 | Ancien run incomplet accepté : validation identité, cohorte, compteurs et hashes avant DecisionContext. | Tests narratifs et parcours complet extraction → approbation → snapshot → scoring → contexte → narration → attribution. |
| B13 | Page placeholder : liste réelle paginée des événements, sans divulgation de l’ancien actor_id contenant parfois une clé. | API et deux scénarios Chromium EN/FR. |
| B14 | Affichage du dernier award seulement : affichage de toute la liste retournée. | Suite décisions existante ; révocation/réattribution live à confirmer. |
| B15 | Sidebar fixe : navigation mobile horizontale et contenu pleine largeur ; contraste des boutons corrigé. | 390 px sans débordement et contrôle axe WCAG. |
| B16 | DNS backend figé : resolver Docker et proxy variable nginx. | Test statique ; recréation backend à confirmer. |
| Worker | Healthcheck HTTP hérité : ping Celery ciblé sur ce worker. | Test statique ; santé du conteneur à confirmer. |

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

## Limites et reprise exacte

Le moteur Docker Linux est inaccessible (`dockerDesktopLinuxEngine` absent) et `docker desktop status` échoue. Les vérifications suivantes **ne sont pas validées** : build/up Compose, santé worker, MIME réel PDF, reconnexion nginx après recréation backend, Alembic current/check et les trois suites docker_live. Aucun volume supprimé.

EN/FR : parité des clés validée, bascule de langue testée, nouveaux états et journal traduits. Les événements d’audit conservent leurs codes techniques canoniques. Le jeu complet des nouvelles erreurs serveur n’est pas encore couvert par une régression bilingue dédiée.

Après démarrage du moteur : construire la pile sans supprimer les volumes, vérifier Alembic et les healthchecks, lancer les suites docker_live, tester le MIME du worker PDF et la reprise DNS. Compléter les régressions navigateur de téléchargement CSV/source et historique revoke/re-award avant de déclarer READY. Ne pousser qu’après tous ces contrôles verts.
