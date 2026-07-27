"""
generate_dataset.py
-------------------
Generates a synthetic dataset of 1000 financing application dossiers
for the BFPME scoring system, then computes the official BFPME score
for each dossier using the exact formula from ScoringService.cs.

Output: bfpme_synthetic_dataset.csv
"""

import sys
sys.path.insert(0, 'd:/BFPME/tmp_pip')

import random
import math
import csv
import openpyxl
from collections import defaultdict

random.seed(42)

# =============================================================================
# STEP 1 — Load all reference tables from BTS_INFO.xlsx
# =============================================================================

wb = openpyxl.load_workbook('BTS_INFO.xlsx')

# RU_Facteur: {code -> libelle}
facteurs = {}
for row in wb['RU_Facteur'].iter_rows(values_only=True):
    if row[0] and row[0] != 'Code':
        facteurs[row[0]] = row[1]

# RU_FacteursParModele: {(modele, facteur) -> (ponderation, ponderation_moyenne)}
facteurs_par_modele = {}
for row in wb['RU_FacteursParModele'].iter_rows(values_only=True):
    if row[0] and row[0] != 'Code':
        facteurs_par_modele[(row[1], row[2])] = {
            'ponderation': row[3],           # Good Financial
            'ponderation_moyenne': row[4]    # Average Financial
        }

# RU_SousFacteur: {code -> {libelle, nature, type}}
sous_facteurs = {}
for row in wb['RU_SousFacteur'].iter_rows(values_only=True):
    if row[0] and row[0] != 'Code':
        sous_facteurs[row[0]] = {
            'libelle': row[1],
            'nature': row[3],
            'type': row[4],
            'non_disponible': row[5]
        }

# RU_SousFacteurParModele: {(modele, sf) -> config}
sf_par_modele = {}
for row in wb['RU_SousFacteurParModele'].iter_rows(values_only=True):
    if row[0] and row[0] != 'Code':
        sf_par_modele[(row[2], row[1])] = {
            'code_sf': row[1],
            'code_modele': row[2],
            'code_facteur': row[3],
            'min_without_kf': row[4] if row[4] is not None else 0,
            'rang': row[5],
            'priorite': row[6] if row[6] is not None else 1,
            'eliminatoire': row[7],
            'accepte_nd': row[9],
            'valeur_obligatoire': row[10]
        }

# RU_CritereNotes: {(modele, sf) -> list of {code_critere, note, borne_inf, borne_sup}}
critere_notes = defaultdict(list)
for row in wb['RU_CritereNotes'].iter_rows(values_only=True):
    if row[0] and row[0] != 'Code':
        key = (row[2], row[3])  # (modele, sf)
        note_val = row[4]
        if isinstance(note_val, str):
            try:
                note_val = float(note_val)
            except:
                note_val = 0
        critere_notes[key].append({
            'code_critere': row[1],
            'note': note_val if note_val is not None else 0,
            'borne_inf': row[6],
            'borne_sup': row[7],
            'eliminatoire': row[10]
        })

# RU_Critere: {code -> libelle}
criteres = {}
for row in wb['RU_Critère'].iter_rows(values_only=True):
    if row[0] and row[0] != 'Code':
        criteres[row[0]] = {'libelle': row[1], 'non_disponible': row[3]}

print("Reference tables loaded.")

# =============================================================================
# STEP 2 — Build model structures
# =============================================================================

def get_sf_list_for_model(modele):
    """Return list of sub-factor configs for a given model, sorted by (facteur, rang)."""
    result = []
    for (mod, sf_code), config in sf_par_modele.items():
        if mod == modele:
            result.append(config)
    result.sort(key=lambda x: (x['code_facteur'], x['rang']))
    return result

# Pre-compute per-model sub-factor lists
model1_sfs = get_sf_list_for_model(1)
model2_sfs = get_sf_list_for_model(2)

def get_available_criteres(modele, sf_code):
    """Return list of available (non-eliminatoire) criteria codes for a sub-factor."""
    key = (modele, sf_code)
    available = critere_notes.get(key, [])
    # Filter out eliminatoire criteria for random generation (we'll add some manually)
    non_elim = [c for c in available if c['note'] > -9999]
    return non_elim if non_elim else available

# =============================================================================
# STEP 3 — Implement CalculWeightsDesSousFacteurs (from ScoringService.cs)
# =============================================================================

def calculate_weights(modele):
    """
    Reimplementation of CalculWeightsDesSousFacteurs().
    Returns dict: {(modele, sf_code) -> {weight_good, weight_average, min_wkf, max_note}}
    """
    weights = {}
    sf_list = get_sf_list_for_model(modele)

    # Group sub-factors by factor
    by_factor = defaultdict(list)
    for sf in sf_list:
        by_factor[sf['code_facteur']].append(sf)

    for facteur_code, sf_in_factor in by_factor.items():
        n = len(sf_in_factor)
        if n == 0:
            continue

        max_prio = max(sf['priorite'] for sf in sf_in_factor)
        # SommeMoyennePrioriteSousfacteur = MaxPrio + 1 - mean(Priorite)
        mean_prio = sum(sf['priorite'] for sf in sf_in_factor) / n
        somme_moy_prio = max_prio + 1 - mean_prio

        pond = facteurs_par_modele.get((modele, facteur_code), {})
        pond_good = pond.get('ponderation', 0)
        pond_avg = pond.get('ponderation_moyenne', 0)

        for sf in sf_in_factor:
            sf_code = sf['code_sf']
            # PrioriteMoyenne = (MaxPrio + 1 - Prio) / N
            prio_moy = (max_prio + 1 - sf['priorite']) / n
            # SubWeights = PrioMoy * 100 / SommeMoyPrio
            sub_w = prio_moy * 100 / somme_moy_prio if somme_moy_prio != 0 else 0
            # WeightGood / WeightAverage
            w_good = sub_w / 100 * pond_good
            w_avg = sub_w / 100 * pond_avg

            # Min and Max notes for this SF in this model
            key = (modele, sf_code)
            notes_list = [c['note'] for c in critere_notes.get(key, [])
                          if isinstance(c['note'], (int, float)) and c['note'] > -9999]
            min_note = min(notes_list) if notes_list else 0
            max_note = max(notes_list) if notes_list else 0
            min_wkf = sf['min_without_kf']

            weights[(modele, sf_code)] = {
                'weight_good': w_good,
                'weight_avg': w_avg,
                'min_note': min_note,
                'max_note': max_note,
                'min_wkf': min_wkf,
                'code_facteur': facteur_code
            }

    return weights

weights_m1 = calculate_weights(1)
weights_m2 = calculate_weights(2)

print(f"Weights computed — Model 1: {len(weights_m1)} sub-factors, Model 2: {len(weights_m2)} sub-factors")

# =============================================================================
# STEP 4 — Compute global normalization bounds per model
# =============================================================================

def compute_global_bounds(modele, weights):
    """Compute MinSomme and MaxSomme for Good and Average scenarios."""
    sum_min_good = 0
    sum_min_avg = 0
    sum_max_good = 0
    sum_max_avg = 0

    for (mod, sf_code), w in weights.items():
        if mod != modele:
            continue
        sum_min_good += w['min_wkf'] * w['weight_good'] / 100
        sum_min_avg  += w['min_wkf'] * w['weight_avg']  / 100
        sum_max_good += w['max_note'] * w['weight_good'] / 100
        sum_max_avg  += w['max_note'] * w['weight_avg']  / 100

    min_global = min(sum_min_good, sum_min_avg)
    max_global = max(sum_max_good, sum_max_avg)
    return {
        'min_good': sum_min_good,
        'min_avg':  sum_min_avg,
        'max_good': sum_max_good,
        'max_avg':  sum_max_avg,
        'min_global': min_global,
        'max_global': max_global
    }

bounds_m1 = compute_global_bounds(1, weights_m1)
bounds_m2 = compute_global_bounds(2, weights_m2)

print(f"Model 1 bounds — Min: {bounds_m1['min_global']:.2f}, Max: {bounds_m1['max_global']:.2f}")
print(f"Model 2 bounds — Min: {bounds_m2['min_global']:.2f}, Max: {bounds_m2['max_global']:.2f}")

# =============================================================================
# STEP 5 — Scoring function (reimplementation of ScoringNotesByProject)
# =============================================================================

def compute_bfpme_score(dossier, modele):
    """
    Compute the BFPME score for a dossier dict {sf_code: critere_code}.
    Returns (score_good, score_average, score_total_good, score_total_average, details).
    """
    weights = weights_m1 if modele == 1 else weights_m2
    bounds  = bounds_m1  if modele == 1 else bounds_m2
    sf_list = model1_sfs if modele == 1 else model2_sfs

    min_global = bounds['min_global']
    max_global = bounds['max_global']
    n = len(sf_list)

    if max_global == min_global:
        return 0, 0, []

    # Check for non-disponible blocking
    existe_non_dispo = False
    for sf in sf_list:
        sf_code = sf['code_sf']
        critere_code = dossier.get(sf_code, 0)
        if critere_code > 0:
            crit_info = criteres.get(critere_code, {})
            if crit_info.get('non_disponible', 0) == 1 and not sf['accepte_nd']:
                existe_non_dispo = True
                break

    total_good = 0
    total_avg = 0
    details = []

    for sf in sf_list:
        sf_code = sf['code_sf']
        critere_code = dossier.get(sf_code, 0)
        w = weights.get((modele, sf_code), {})
        w_good = w.get('weight_good', 0)
        w_avg  = w.get('weight_avg', 0)

        # Get note attribuee
        note = 0
        if critere_code > 0:
            crit_info = criteres.get(critere_code, {})
            is_nd = crit_info.get('non_disponible', 0) == 1

            if not is_nd:
                # CAS 1: normal — look up note in critere_notes
                key = (modele, sf_code)
                matched = [c for c in critere_notes.get(key, []) if c['code_critere'] == critere_code]
                note = matched[0]['note'] if matched else 0
                if isinstance(note, str):
                    note = 0
                if note <= -9999:
                    note = -9999
            else:
                # CAS 2: non-disponible — use average of valid notes
                key = (modele, sf_code)
                valid_notes = [c['note'] for c in critere_notes.get(key, [])
                               if isinstance(c['note'], (int, float)) and c['note'] >= -70]
                note = sum(valid_notes) / len(valid_notes) if valid_notes else 0

        # Eliminatoire: use a strong penalty note instead of breaking
        if note <= -9999:
            note = -200

        note_pond_good = note * w_good / 100
        note_pond_avg  = note * w_avg  / 100

        if existe_non_dispo:
            score_good = 0
            score_avg  = 0
        else:
            score_good = ((note_pond_good - min_global / n) * 200 / (max_global - min_global)) + 100 / n
            score_avg  = ((note_pond_avg  - min_global / n) * 200 / (max_global - min_global)) + 100 / n

        total_good += score_good
        total_avg  += score_avg

        details.append({
            'sf_code': sf_code,
            'critere_code': critere_code,
            'note': note,
            'weight_good': w_good,
            'weight_avg': w_avg,
            'score_good': round(score_good, 4),
            'score_avg': round(score_avg, 4)
        })

    return round(total_good, 4), round(total_avg, 4), details

# =============================================================================
# STEP 6 — Generate 1000 synthetic dossiers
# =============================================================================

def generate_dossier(modele):
    """Randomly generate a dossier for the given model."""
    sf_list = model1_sfs if modele == 1 else model2_sfs
    dossier = {}

    for sf in sf_list:
        sf_code = sf['code_sf']
        available = get_available_criteres(modele, sf_code)
        if not available:
            dossier[sf_code] = 0
            continue

        # 2% chance of picking an eliminatoire critere to create rejected dossiers
        all_criteres = critere_notes.get((modele, sf_code), [])
        elim_criteres = [c for c in all_criteres if c['note'] <= -9999]

        if elim_criteres and random.random() < 0.03:
            chosen = random.choice(elim_criteres)
        else:
            chosen = random.choice(available)

        dossier[sf_code] = chosen['code_critere']

    return dossier

# All sub-factor codes across both models (for column headers)
all_sf_codes_m1 = sorted(set(sf['code_sf'] for sf in model1_sfs))
all_sf_codes_m2 = sorted(set(sf['code_sf'] for sf in model2_sfs))
all_sf_codes = sorted(set(all_sf_codes_m1 + all_sf_codes_m2))

records = []
n_model1 = 0
n_model2 = 0

for i in range(1000):
    # 55% model 1 (creation), 45% model 2 (extension)
    modele = 1 if random.random() < 0.55 else 2

    dossier = generate_dossier(modele)
    score_good, score_avg, details = compute_bfpme_score(dossier, modele)

    # Determine risk class based on score_good
    if score_good <= 20:
        risk_class = 'Rejete'
    elif score_good < 80:
        risk_class = 'Tres_Risque'
    elif score_good < 120:
        risk_class = 'Risque'
    elif score_good < 160:
        risk_class = 'Moyen'
    elif score_good < 200:
        risk_class = 'Bon'
    else:
        risk_class = 'Excellent'

    row = {
        'dossier_id': f'DOS_{i+1:04d}',
        'code_modele': modele,
    }

    # Add sub-factor columns (NaN for SF not in this model)
    for sf_code in all_sf_codes:
        col_name = f'SF_{sf_code}'
        row[col_name] = dossier.get(sf_code, None)

    row['score_bfpme_good']    = score_good
    row['score_bfpme_average'] = score_avg
    row['risk_class']          = risk_class

    records.append(row)
    if modele == 1:
        n_model1 += 1
    else:
        n_model2 += 1

print(f"\nGenerated {len(records)} dossiers: {n_model1} Model 1 (Creation), {n_model2} Model 2 (Extension)")

# =============================================================================
# STEP 7 — Save to CSV
# =============================================================================

output_file = 'bfpme_synthetic_dataset.csv'
fieldnames = list(records[0].keys())

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"Dataset saved to: {output_file}")
print(f"Shape: {len(records)} rows x {len(fieldnames)} columns")

# Quick stats
scores_good = [r['score_bfpme_good'] for r in records]
scores_avg  = [r['score_bfpme_average'] for r in records]
rejected    = sum(1 for r in records if r['risk_class'] == 'Rejete')
classes     = defaultdict(int)
for r in records:
    classes[r['risk_class']] += 1

print(f"\n=== Score Statistics (Good Financial) ===")
print(f"  Min    : {min(scores_good):.2f}")
print(f"  Max    : {max(scores_good):.2f}")
print(f"  Mean   : {sum(scores_good)/len(scores_good):.2f}")

print(f"\n=== Risk Class Distribution ===")
for cls, count in sorted(classes.items(), key=lambda x: -x[1]):
    print(f"  {cls:<15} : {count:>4} dossiers ({count/10:.1f}%)")

print(f"\nDone. File ready: {output_file}")
