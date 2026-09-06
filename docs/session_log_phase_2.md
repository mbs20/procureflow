# ProcureFlow - Journal de Session & Historique des Échanges (Phase 2 & Hardening)

**Date :** 06 Septembre 2026  
**Identifiant de conversation :** `81a7928a-e36e-44d5-bceb-b2e893894d41`  
**Dépôt :** [mbs20/procureflow](https://github.com/mbs20/procureflow)  
**Branche :** `main`  
**Dernier Commit :** [`81e2be5`](https://github.com/mbs20/procureflow/commit/81e2be5) (`fix(quotation): harden OCR end-to-end flow, extraction versioning, and evidence naming`)

---

## 1. Emplacement des Transcriptions Système Automatiques

L'environnement Antigravity enregistre l'intégralité brute et chronologique de chaque message, prompt et appel d'outil sous format JSON Lines (JSONL) aux emplacements locaux suivants :

- **Transcription compacte :**  
  `C:\Users\HP Elitebook G8 T\.gemini\antigravity-ide\brain\81a7928a-e36e-44d5-bceb-b2e893894d41\.system_generated\logs\transcript.jsonl`
- **Transcription intégrale non tronquée :**  
  `C:\Users\HP Elitebook G8 T\.gemini\antigravity-ide\brain\81a7928a-e36e-44d5-bceb-b2e893894d41\.system_generated\logs\transcript_full.jsonl`
- **Artefacts et Plans :**  
  `C:\Users\HP Elitebook G8 T\.gemini\antigravity-ide\brain\81a7928a-e36e-44d5-bceb-b2e893894d41\walkthrough.md`  
  `C:\Users\HP Elitebook G8 T\.gemini\antigravity-ide\brain\81a7928a-e36e-44d5-bceb-b2e893894d41\implementation_plan.md`

---

## 2. Synthèse Chronologique des Décisions et Échanges

### Étape 1 : Stabilisation Docker & Packaging Python
- **Constat initial :** Échec de `uv pip install -e ".[dev]"` lors du build Docker backend/worker en raison de l'absence du `README.md` dans le contexte Docker.
- **Résolution :** Réorganisation de l'ordre de copie dans `backend/Dockerfile` pour garantir la présence des métadonnées du package, et exclusion via `.dockerignore` des caches lourds.
- **Validation :** Build Docker validé, passage au déploiement initial sur GitHub.

### Étape 2 : Cadrage Architectural de la Phase 2
- **Exclusion du format .xls hérité :** Rejet explicite avec HTTP 422 invitant à convertir en `.xlsx`. Pas de dépendance tierce superflue.
- **Principe Human-in-the-Loop :** L'extraction automatique se termine impérativement au statut `needs_review`. Le passage à `approved` requiert une validation explicite par un relecteur humain.
- **Origine déterministe des coordonnées de preuves (Source Evidence) :** Le LLM ne doit jamais inventer de coordonnées spatiales ou de numéros de page. Celles-ci proviennent à 100% des parseurs déterministes (PyMuPDF, OpenPyXL, CSV sniffer, Tesseract).
- **Historique et Immutabilité des Documents :** Les documents sources sont stockés de manière immuable avec hachage SHA-256 et horodatage. Les extractions successives sont archivées (`is_current = false`) pour préserver l'auditabilité.

### Étape 3 : Implémentation de la Phase 2 (Ingestion & Extraction)
- Implémentation du service de stockage (`StorageService`) avec isolation et vérification de type MIME magique.
- Parseurs modulaires : `CSVExtractor`, `ExcelExtractor`, `PDFExtractor`, `OCREngine`.
- Pipeline d'orchestration : association automatique aux lignes RFQ basée sur la similarité lexicale et pondération.
- Tâche asynchrone Celery (`extract_quotation_task`) idempotente.
- Interface utilisateur React moderne avec visualiseur de coordonnées spatiales / tableur et mode relecture/correction en ligne.
- Validation GitHub Actions CI : commit [`912f9aa`](https://github.com/mbs20/procureflow/commit/912f9aa).

### Étape 4 : Passe Finale de Durcissement (Hardening Pass)
Quatre contraintes clés résolues et validées :
1. **Validation OCR PDF scanné de bout en bout :**
   - Test automatisé complet utilisant le PDF scanné réel [`scanned_quote_image.pdf`](file:///c:/Users/HP%20Elitebook%20G8%20T/Desktop/WEBSITES%20PROJECTS/open%20source%20project/backend/tests/fixtures/quotations/scanned_quote_image.pdf) (6,5 Mo).
   - Validation de la chaîne : détection du scan ➔ déclenchement OCR ➔ récupération du texte ➔ extraction structurée ➔ persistance des coordonnées OCR (`ocr_pdf`, page 1, score de confiance >= 0.8, boîte englobante).
2. **Gestion de version d'extraction & Idempotence :**
   - Vérification que la version 1 est préservée lors d'une ré-extraction et bascule à `is_current = False`.
   - La version 2 devient `is_current = True`.
   - Un index partiel unique en base de données (`uq_current_extraction_per_quotation`) garantit qu'exactement une extraction est active par devis à tout moment.
   - Les relances/retries Celery ne peuvent créer aucun doublon d'extraction active.
3. **Distinction Prix Quoted vs Prix Calculated :**
   - Modélisation distincte de `total_price` (valeur fournie par le fournisseur) et de `calculated_total_price` (calculé par ProcureFlow : `quantité × prix unitaire`).
   - L'édition de la quantité ou du prix unitaire met à jour la valeur calculée sans écraser la valeur originale du fournisseur, signalant une anomalie (`has_discrepancy = true`) tant qu'une correction explicite n'est pas saisie.
4. **Nettoyage et standardisation du modèle de preuve (`source_evidence`) :**
   - Remplacement de l'ancien nommage `source_bbox` par l'objet générique `source_evidence`.
   - Propriété `bbox` restreinte aux formats spatiaux (`pdf`, `ocr_pdf`), tandis que `spreadsheet` expose `sheet`, `row`, `cells`. Rétrocompatibilité interne maintenue via alias déprécié.

---

## 3. Statut des Tests et de l'Intégration Continue (CI)

| Composant | Commande | Résultat |
|---|---|---|
| Tests Unitaires & Intégration Backend | `pytest tests/unit/ tests/integration/ -v` | **32 passés, 0 échec** |
| Linting & Formatage Backend | `ruff check . && ruff format --check .` | **Conforme à 100%** |
| Typage & Build Frontend | `tsc --noEmit && vite build` | **0 erreur, bundle généré** |
| Conteneurs Docker | `docker compose ps` | **5/5 conteneurs sains (healthy)** |
| GitHub Actions CI | Run #34018273796 | **Succès complet (Vert)** |

---

## 4. Prochaine Étape : Phase 3
Phase 2 étant formellement achevée et validée, le projet est prêt pour entamer la **Phase 3 — Comparison Matrix, Normalization & Scoring**.
