# Rapport Technique - Projet PD Classification (BFPME)

## 1) Contexte et objectif du projet

Ce projet vise a construire une base de travail pour la prediction du risque de defaut (PD) dans un cadre de modernisation progressive du scoring BFPME.

L'approche retenue est prudente:
- conserver la logique metier existante BFPME comme reference,
- creer un dataset centralise enrichi,
- tester des modeles de classification ML (RandomForest, XGBoost),
- comparer plusieurs strategies d'integration du signal BFPME.

Le but n'est pas de remplacer immediatement le scorecard historique, mais de demontrer une valeur ajoutee methodologique dans un cadre champion/challenger.

---

## 2) Creation de `data/dataset_final.csv`

### 2.1 Source de depart

Le fichier `data/dataset_final.csv` a ete construit a partir de:
- `data/bfpme_synthetic_dataset.csv` (base initiale contenant sous-facteurs BFPME, score et classes de risque),
- script de generation: `scripts/generate_dataset_final.py`.

La base finale contient:
- les variables d'origine BFPME (sous-facteurs + scores),
- des variables synthetiques additionnelles (business, credit, finance, garanties, comportement bancaire, macro),
- des ratios derives,
- une cible de classification binaire: `default_flag`.

### 2.2 Structure du dataset final

Le dataset final est centralise ("wide table"):
- 1 ligne = 1 dossier client
- 1 colonne = 1 variable explicative ou cible

Il contient notamment:
- identifiants et metadonnees (`dossier_id`, `code_modele`),
- variables BFPME (`score_bfpme_*`, `risk_class`, `SF_*`),
- variables metier enrichies (juridique, taille, gouvernance, localisation, credit),
- variables financieres (structure bilan, rentabilite, liquidite, cashflow),
- variables comportementales et relation bancaire (DPD, impayes, discipline),
- variables macroeconomiques (`scenario_macro`, inflation, PIB, etc.),
- cible: `default_flag` (0/1) + variable intermediaire `pd_target`.

---

## 3) Logique de generation metier et formule latente de la cible

## 3.1 Principe general

Le dataset a ete genere avec une logique de coherence metier, et non par tirage totalement aleatoire.

Une variable cachee est introduite:
- `latent_risk` (niveau de risque latent),
- `latent_quality = 1 - latent_risk`.

Cette variable gouverne ensuite de nombreuses distributions:
- profils solides -> meilleure liquidite, meilleure gouvernance, meilleur comportement de paiement,
- profils fragiles -> endettement plus eleve, DPD plus fort, stress bancaire plus marque.

## 3.2 Construction du risque latent

Le risque latent est calcule a partir de:
- score BFPME global normalise,
- index de risque derive de la classe BFPME (`bfpme_risk_index`),
- type de modele (`code_modele`),
- bruit gaussien modere.

Forme simplifiee:

`latent_risk ~= 0.55 * base_risk + 0.35 * bfpme_risk_index + 0.10 * I(code_modele=1) + bruit`

avec:
- `base_risk = 1 - score_bfpme_global / 200`.

## 3.3 Generation de `pd_target`

La probabilite de defaut intermediaire est obtenue via un score latent de defaut, combine avec une fonction logistique (sigmoid).

Le score latent de defaut agrege:

**Effets qui augmentent le risque**:
- faible score BFPME,
- DPD moyen eleve,
- leverage eleve (`debt_to_equity_ratio`),
- faible capacite de service de la dette (`dscr` faible),
- conditions macro defavorables,
- comportements de stress (augmentation dettes, baisse depots, etc.).

**Effets qui reduisent le risque**:
- meilleure liquidite (`ratio_liquidite_generale`),
- meilleure couverture de garanties (`garantie_coverage_ratio`),
- meilleur taux de remboursement ponctuel,
- meilleure confiance institutionnelle.

Forme simplifiee:

`pd_target = sigmoid(score_latent_default)`

## 3.4 Construction de la cible binaire `default_flag`

La cible finale de classification est un tirage Bernoulli:

`default_flag ~ Bernoulli(pd_target)`

Donc:
- `default_flag = 1`: defaut,
- `default_flag = 0`: non-defaut.

Cette approche permet de transformer une logique de probabilite en probleme supervise binaire.

---

## 4) Data preprocessing & feature engineering

Notebook de reference:
- `notebook/data_preprocessing_feature_engineering.ipynb`

### 4.1 Etapes de preprocessing appliquees

1. Chargement et controles initiaux:
- dimensions du dataset,
- types,
- taux de valeurs manquantes,
- distribution de la cible.

2. Controle de fuite d'information:
- suppression de `pd_target` (utilisee pour generer la cible),
- suppression de l'identifiant `dossier_id`.

3. Analyse exploratoire ciblee:
- visualisation de `default_flag`,
- distributions/boxplots de variables cle (score BFPME, DPD, liquidite, garanties, leverage, DSCR).

4. Detection des outliers:
- methode IQR sur variables cle.

5. Winsorization ciblee:
- clipping quantiles (1% / 99%) sur variables financieres extremes.

6. Encodage categoriel controle:
- `OrdinalEncoder` pour categories ordonnees,
- `OneHotEncoder` limite aux variables nominales necessaires.

7. Standardisation:
- `StandardScaler` sur variables numeriques.

8. Split train/test:
- split stratifie (80/20) sur `default_flag`.

9. Export:
- jeux preprocesses (`X_train_preprocessed`, `X_test_preprocessed`, `y_train`, `y_test`).

### 4.2 Feature engineering metier ajoute

Variables composites principales:
- `debt_total = dettes_court_terme + dettes_long_terme`,
- `loan_to_revenue = montant_pret / chiffre_affaires_annuel`,
- `cash_to_debt = cash_equivalents / debt_total`,
- `impayes_to_loan = montant_impayes / montant_pret`,
- `stress_behavior_index` (somme de signaux de stress bancaire),
- `governance_risk_index` (experience + turnover + structure dirigeante).

Ces variables visent a mieux capter:
- pression de dette,
- fragilite de tresorerie,
- stress comportemental,
- risque de gouvernance.

---

## 5) Strategie de modelisation: 3 options comparees

Trois notebooks de classification ont ete crees:
- `notebook/classification_option_A_all_features.ipynb`
- `notebook/classification_option_B_without_bfpme.ipynb`
- `notebook/classification_option_C_hybrid_min_bfpme.ipynb`

Chaque notebook entraine:
- `RandomForestClassifier`
- `XGBoost` (ou fallback GradientBoosting si xgboost indisponible)

### Option A - All Features

**Objectif**
- mesurer la performance maximale avec toutes les variables utiles.

**Contenu**
- variables enrichies + signaux BFPME complets (scores et classe).

**Lecture metier**
- benchmark "upper bound" de performance.

### Option B - Without BFPME Score Family

**Objectif**
- evaluer la capacite predictive d'un modele plus "data-driven", moins dependant du score historique.

**Contenu**
- retrait des variables de score BFPME et classes associees.

**Lecture metier**
- mesure de la valeur predictive des nouvelles variables hors scorecard legacy.

### Option C - Hybrid Minimal BFPME

**Objectif**
- tester une approche hybride parcimonieuse.

**Contenu**
- conservation d'un seul signal BFPME (`score_bfpme_global`), retrait du reste de la famille score detaillee.

**Lecture metier**
- compromis entre explicabilite metier historique et signal data-driven.

---

## 6) Resultats observes et interpretation

Les resultats observes sont tres eleves (accuracy/F1/AUC autour de 0.96-0.99) sur les trois options.

Exemple de constat:
- performances proches entre A/B/C,
- AUC tres elevees pour tous les modeles,
- faibles ecarts entre RandomForest et XGBoost.

## 6.1 Pourquoi ces resultats paraissent "incoherents" (trop bons)

Ce comportement est attendu dans ce contexte synthetique:

1. La cible `default_flag` est generee a partir d'une formule latente qui reutilise explicitement des signaux presents en entree.

2. Le dataset est structure avec une forte coherence interne (peu de bruit "reel" non modele).

3. Plusieurs variables ont une relation quasi deterministe avec la cible (DPD, score, stress, liquidite).

4. Le split aleatoire train/test conserve des distributions tres proches entre apprentissage et test.

Conclusion:
- ces performances valident la coherence technique du pipeline,
- mais elles ne representent pas un niveau de performance realiste attendu en production sur donnees reelles.

---

## 7) Perspectives d'amelioration (prioritaires)

Pour rendre l'exercice plus robuste et plus proche d'un contexte bancaire reel, les axes suivants sont recommandes:

1. **Ajouter plus de bruit/stochasticite dans la generation de `default_flag`**
- augmenter la part aleatoire non expliquee par les features,
- reduire le caractere deterministe de la cible.

2. **Reduire le poids des variables dominantes (`score_bfpme_global`, DPD, etc.)**
- reequilibrer la formule latente,
- renforcer le role de signaux secondaires (gouvernance, macro, garanties, trajectoire business).

3. **Introduire des contradictions realistes**
- bons dossiers qui defautent (chocs exogenes, risque operationnel),
- dossiers risques qui tiennent (resilience, soutiens externes, adaptation).

4. **Utiliser un split temporel au lieu d'un split aleatoire**
- train = historique passe,
- test = periode future,
- meilleure simulation de la realite de deploiement.

---

## 8) Livrables techniques existants

- Dataset final:
  - `data/dataset_final.csv`

- Documentation variables:
  - `dataset_final_variable_dictionary.txt`

- Generation du dataset:
  - `scripts/generate_dataset_final.py`

- Preprocessing & feature engineering:
  - `notebook/data_preprocessing_feature_engineering.ipynb`

- Classification (3 options):
  - `notebook/classification_option_A_all_features.ipynb`
  - `notebook/classification_option_B_without_bfpme.ipynb`
  - `notebook/classification_option_C_hybrid_min_bfpme.ipynb`

---

## 9) Conclusion

Le projet fournit un cadre complet et presentable de modelisation PD en mode "proof of value":
- conception de donnees enrichies,
- cible de classification binaire,
- pipeline reproductible,
- comparaison strategique A/B/C.

Les performances observees sont volontairement "optimistes" compte tenu de la nature synthetique du dataset. Cette etape reste toutefois tres utile pour:
- industrialiser la methodologie,
- aligner les equipes risque/data,
- preparer la transition vers un challenger modele sur donnees reelles BFPME.

