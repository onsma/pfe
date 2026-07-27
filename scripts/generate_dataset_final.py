import numpy as np
import pandas as pd


SEED = 42
rng = np.random.default_rng(SEED)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def clip_series(s, low=None, high=None):
    if low is not None:
        s = np.maximum(s, low)
    if high is not None:
        s = np.minimum(s, high)
    return s


base_path = r"d:\BFPME\data\bfpme_synthetic_dataset.csv"
output_path = r"d:\BFPME\data\dataset_final.csv"

df = pd.read_csv(base_path)
out = df.copy()
n = len(out)

# Core BFPME features
out["score_bfpme_global"] = np.where(
    out["code_modele"] == 1, out["score_bfpme_average"], out["score_bfpme_good"]
)
out["score_bfpme_gap"] = out["score_bfpme_good"] - out["score_bfpme_average"]

risk_map = {
    "Excellent": 0.08,
    "Bon": 0.22,
    "Moyen": 0.45,
    "Risque": 0.68,
    "Tres_Risque": 0.85,
    "Rejete": 0.97,
}
out["bfpme_risk_index"] = out["risk_class"].map(risk_map).fillna(0.5)

# Hidden latent quality/risk driver
score_norm = clip_series(out["score_bfpme_global"] / 200.0, 0.0, 1.0)
base_risk = 1.0 - score_norm
latent_risk = clip_series(
    0.55 * base_risk
    + 0.35 * out["bfpme_risk_index"]
    + 0.10 * (out["code_modele"] == 1).astype(float)
    + rng.normal(0, 0.05, n),
    0.01,
    0.99,
)
latent_quality = 1.0 - latent_risk


def weighted_choice(options, probs_matrix):
    idx = [rng.choice(len(options), p=p) for p in probs_matrix]
    return [options[i] for i in idx]


# Business identity
juridical_probs = []
for q in latent_quality:
    if q > 0.72:
        juridical_probs.append([0.55, 0.30, 0.15])  # SARL, SA, EI
    elif q > 0.45:
        juridical_probs.append([0.62, 0.15, 0.23])
    else:
        juridical_probs.append([0.50, 0.05, 0.45])
out["structure_juridique"] = weighted_choice(
    ["SARL", "SA", "Entreprise_individuelle"], juridical_probs
)

employees = np.round(
    4 + 120 * latent_quality + rng.normal(0, 10, n)
).astype(int)
employees = clip_series(employees, 1, 250)
out["nombre_employes"] = employees

out["classification_pme"] = np.select(
    [employees <= 9, employees <= 49, employees <= 250],
    ["micro", "petite", "moyenne"],
    default="moyenne",
)

capital_social = (
    30000
    + 1200000 * latent_quality
    + np.where(np.array(out["structure_juridique"]) == "SA", 400000, 0)
    + rng.normal(0, 80000, n)
)
out["capital_social"] = np.round(clip_series(capital_social, 5000, None), 2)

associe_dom = (
    0.35 + 0.40 * latent_risk + rng.normal(0, 0.08, n)
)
out["associes_dominants_pct"] = np.round(100 * clip_series(associe_dom, 0.15, 0.95), 2)

ca_annuel = (
    employees * (90000 + 50000 * latent_quality)
    + out["capital_social"] * (0.5 + 1.5 * latent_quality)
    + rng.normal(0, 400000, n)
)
out["chiffre_affaires_annuel"] = np.round(clip_series(ca_annuel, 80000, None), 2)

part_marche = 0.01 + 0.18 * latent_quality + rng.normal(0, 0.02, n)
out["part_marche_estimee_pct"] = np.round(100 * clip_series(part_marche, 0.005, 0.35), 2)

competition_probs = []
for r in latent_risk:
    if r > 0.75:
        competition_probs.append([0.10, 0.25, 0.45, 0.20])
    elif r > 0.45:
        competition_probs.append([0.15, 0.40, 0.35, 0.10])
    else:
        competition_probs.append([0.28, 0.45, 0.22, 0.05])
out["niveau_concurrence_local"] = weighted_choice(
    ["faible", "moyenne", "forte", "tres_forte"], competition_probs
)

dep_client = 0.10 + 0.55 * latent_risk + rng.normal(0, 0.08, n)
out["dependance_client_unique_pct"] = np.round(
    100 * clip_series(dep_client, 0.03, 0.95), 2
)

# Governance and location
multi_leaders_prob = clip_series(0.25 + 0.50 * latent_quality, 0.10, 0.90)
out["existence_dirigeants_multiples"] = (
    rng.random(n) < multi_leaders_prob
).astype(int)

experience = np.round(2 + 22 * latent_quality + rng.normal(0, 3, n)).astype(int)
out["experience_dirigeant_principal"] = clip_series(experience, 0, 40)

turnover = np.round(4 * latent_risk + rng.normal(0, 0.7, n)).astype(int)
out["turnover_direction_3ans"] = clip_series(turnover, 0, 6)

zone_probs = []
for q in latent_quality:
    if q > 0.70:
        zone_probs.append([0.50, 0.35, 0.15])
    elif q > 0.40:
        zone_probs.append([0.42, 0.28, 0.30])
    else:
        zone_probs.append([0.30, 0.15, 0.55])
out["zone_localisation"] = weighted_choice(
    ["urbaine", "industrielle", "rurale"], zone_probs
)

infra = np.round(2 + 3 * latent_quality + rng.normal(0, 0.7, n), 1)
out["acces_infrastructures_score"] = clip_series(infra, 1.0, 5.0)

# Credit characteristics
objectif_probs = []
for code in out["code_modele"]:
    if code == 1:
        objectif_probs.append([0.55, 0.30, 0.15])
    else:
        objectif_probs.append([0.25, 0.20, 0.55])
out["objectif_credit"] = weighted_choice(
    ["investissement", "exploitation", "expansion"], objectif_probs
)

type_probs = []
for obj in out["objectif_credit"]:
    if obj == "exploitation":
        type_probs.append([0.20, 0.65, 0.15])
    elif obj == "expansion":
        type_probs.append([0.10, 0.35, 0.55])
    else:
        type_probs.append([0.25, 0.50, 0.25])
out["type_credit"] = weighted_choice(
    ["court_terme", "moyen_terme", "long_terme"], type_probs
)

investment = (
    out["chiffre_affaires_annuel"] * (0.15 + 0.55 * rng.random(n))
    + 70000 * out["code_modele"]
)
out["montant_total_investissement"] = np.round(clip_series(investment, 50000, None), 2)

personal_contrib_ratio = clip_series(
    0.12 + 0.38 * latent_quality + rng.normal(0, 0.05, n), 0.05, 0.70
)
out["apport_personnel"] = np.round(
    out["montant_total_investissement"] * personal_contrib_ratio, 2
)

cofin_prob = clip_series(0.20 + 0.35 * latent_quality, 0.05, 0.75)
out["cofinancement"] = (rng.random(n) < cofin_prob).astype(int)
out["credit_rattache"] = (rng.random(n) < (0.15 + 0.25 * latent_risk)).astype(int)

loan_amount = (
    out["montant_total_investissement"]
    - out["apport_personnel"]
    - out["cofinancement"] * out["montant_total_investissement"] * (0.08 + 0.15 * rng.random(n))
)
out["montant_pret"] = np.round(clip_series(loan_amount, 20000, None), 2)

guarantee_probs = []
for q in latent_quality:
    if q > 0.70:
        guarantee_probs.append([0.35, 0.12, 0.35, 0.18])
    elif q > 0.45:
        guarantee_probs.append([0.42, 0.22, 0.15, 0.21])
    else:
        guarantee_probs.append([0.32, 0.38, 0.05, 0.25])
out["garantie_type"] = weighted_choice(
    ["hypotheque", "caution_personnelle", "garantie_bancaire", "nantissement"],
    guarantee_probs,
)

liq_map = {
    "hypotheque": "moyenne",
    "caution_personnelle": "difficile",
    "garantie_bancaire": "facile",
    "nantissement": "moyenne",
}
decote_map = {
    "hypotheque": 0.25,
    "caution_personnelle": 0.45,
    "garantie_bancaire": 0.10,
    "nantissement": 0.30,
}
coverage_base = {
    "hypotheque": 1.10,
    "caution_personnelle": 0.65,
    "garantie_bancaire": 0.95,
    "nantissement": 0.85,
}
garantie_valeur = []
liquidite = []
decote = []
for gt, q, amount in zip(out["garantie_type"], latent_quality, out["montant_pret"]):
    cover = coverage_base[gt] + 0.35 * (q - 0.5) + rng.normal(0, 0.12)
    garantie_valeur.append(max(0.3, cover) * amount)
    liquidite.append(liq_map[gt])
    decote.append(decote_map[gt] + rng.normal(0, 0.03))
out["garantie_valeur"] = np.round(garantie_valeur, 2)
out["garantie_liquidite"] = liquidite
out["garantie_decote_pct"] = np.round(100 * clip_series(np.array(decote), 0.05, 0.65), 2)

duration_map = {"court_terme": 18, "moyen_terme": 48, "long_terme": 84}
duration_noise = rng.integers(-6, 7, n)
out["duree_mois"] = clip_series(
    np.array([duration_map[t] for t in out["type_credit"]]) + duration_noise,
    6,
    120,
)
out["duree_credit"] = np.select(
    [out["duree_mois"] <= 24, out["duree_mois"] <= 60, out["duree_mois"] > 60],
    ["court_terme", "moyen_terme", "long_terme"],
    default="moyen_terme",
)

# Macroeconomic environment
macro_scenarios = weighted_choice(
    ["base", "adverse", "severe"],
    [[0.60, 0.30, 0.10] for _ in range(n)],
)
out["scenario_macro"] = macro_scenarios
macro_params = {
    "base": (0.055, 0.065, 0.030, 0.110, 0.35, 0.30, 0),
    "adverse": (0.075, 0.085, 0.015, 0.135, 0.55, 0.50, 1),
    "severe": (0.095, 0.105, -0.010, 0.165, 0.78, 0.72, 1),
}
inflation = []
taux_directeur = []
croissance_pib = []
chomage = []
risque_sectoriel_global = []
risque_pays_region = []
choc_economique = []
for sc in macro_scenarios:
    vals = macro_params[sc]
    inflation.append(vals[0] + rng.normal(0, 0.005))
    taux_directeur.append(vals[1] + rng.normal(0, 0.006))
    croissance_pib.append(vals[2] + rng.normal(0, 0.006))
    chomage.append(vals[3] + rng.normal(0, 0.008))
    risque_sectoriel_global.append(vals[4] + rng.normal(0, 0.06))
    risque_pays_region.append(vals[5] + rng.normal(0, 0.06))
    choc_economique.append(vals[6])
out["inflation"] = np.round(100 * clip_series(np.array(inflation), 0.01, 0.20), 2)
out["taux_directeur"] = np.round(100 * clip_series(np.array(taux_directeur), 0.02, 0.20), 2)
out["croissance_pib"] = np.round(100 * clip_series(np.array(croissance_pib), -0.08, 0.10), 2)
out["taux_chomage"] = np.round(100 * clip_series(np.array(chomage), 0.04, 0.30), 2)
out["risque_sectoriel_global"] = np.round(100 * clip_series(np.array(risque_sectoriel_global), 0.05, 0.99), 2)
out["risque_pays_region"] = np.round(100 * clip_series(np.array(risque_pays_region), 0.05, 0.99), 2)
out["choc_economique"] = choc_economique

sector_project_risk = (
    out["risque_sectoriel_global"] / 100
    + 0.10 * (np.array(out["niveau_concurrence_local"]) == "forte")
    + 0.18 * (np.array(out["niveau_concurrence_local"]) == "tres_forte")
    + rng.normal(0, 0.05, n)
)
out["niveau_risque_sectoriel_projet"] = np.round(
    100 * clip_series(sector_project_risk, 0.05, 0.99), 2
)

# Financial structure
equity_ratio = clip_series(0.15 + 0.45 * latent_quality + rng.normal(0, 0.05, n), 0.05, 0.75)
out["capitaux_propres"] = np.round(
    clip_series(out["chiffre_affaires_annuel"] * (0.20 + equity_ratio), 20000, None), 2
)

debt_total = out["montant_pret"] * (1.00 + 0.35 * rng.random(n)) + out["chiffre_affaires_annuel"] * (
    0.10 + 0.35 * latent_risk
)
debt_total = clip_series(debt_total, 5000, None)
lt_share = clip_series(0.35 + 0.35 * rng.random(n), 0.20, 0.80)
out["dettes_long_terme"] = np.round(debt_total * lt_share, 2)
out["dettes_court_terme"] = np.round(debt_total * (1 - lt_share), 2)

out["fdr"] = np.round(
    clip_series(out["capitaux_propres"] * (0.15 + 0.70 * latent_quality) + rng.normal(0, 30000, n), -50000, None),
    2,
)
out["bfr"] = np.round(
    clip_series(out["chiffre_affaires_annuel"] * (0.05 + 0.25 * latent_risk) + rng.normal(0, 40000, n), 5000, None),
    2,
)
out["cash_equivalents"] = np.round(
    clip_series(out["chiffre_affaires_annuel"] * (0.03 + 0.15 * latent_quality) + rng.normal(0, 30000, n), 1000, None),
    2,
)

out["actifs_courants"] = np.round(
    clip_series(out["cash_equivalents"] + out["bfr"] * (1.2 + 0.8 * latent_quality), 5000, None), 2
)
out["passifs_courants"] = np.round(
    clip_series(out["dettes_court_terme"] * (0.7 + 0.7 * latent_risk), 1000, None), 2
)

out["ebitda"] = np.round(
    clip_series(out["chiffre_affaires_annuel"] * (0.06 + 0.24 * latent_quality) + rng.normal(0, 60000, n), -100000, None),
    2,
)
gross_margin = clip_series(0.18 + 0.38 * latent_quality + rng.normal(0, 0.05, n), 0.05, 0.75)
out["marge_brute_pct"] = np.round(100 * gross_margin, 2)
net_margin = clip_series(0.01 + 0.16 * latent_quality - 0.12 * latent_risk + rng.normal(0, 0.03, n), -0.20, 0.35)
out["marge_nette_pct"] = np.round(100 * net_margin, 2)

out["resultat_net"] = np.round(out["chiffre_affaires_annuel"] * net_margin, 2)
total_assets = clip_series(
    out["capitaux_propres"] + out["dettes_court_terme"] + out["dettes_long_terme"] + out["cash_equivalents"],
    10000,
    None,
)
out["total_bilan"] = np.round(total_assets, 2)
out["roa_pct"] = np.round(100 * (out["resultat_net"] / total_assets), 2)
out["roe_pct"] = np.round(100 * (out["resultat_net"] / clip_series(out["capitaux_propres"], 5000, None)), 2)

annual_rate = (out["taux_directeur"] / 100) + 0.03 + 0.08 * latent_risk
annual_rate += np.where(out["type_credit"] == "court_terme", 0.01, 0.0)
annual_rate = clip_series(annual_rate, 0.04, 0.28)
out["taux_interet_effectif_reel"] = np.round(100 * annual_rate, 2)
out["frais_annexes"] = np.round(
    out["montant_pret"] * clip_series(0.005 + 0.015 * latent_risk + rng.normal(0, 0.002, n), 0.002, 0.04),
    2,
)
out["teg"] = np.round(
    out["taux_interet_effectif_reel"] + 100 * (out["frais_annexes"] / clip_series(out["montant_pret"], 1000, None)),
    2,
)
out["cout_credit"] = np.round(
    out["montant_pret"] * annual_rate * (out["duree_mois"] / 12) + out["frais_annexes"], 2
)
out["sensibilite_taux"] = weighted_choice(
    ["fixe", "variable", "mixte"],
    [[0.55, 0.20, 0.25] if sc == "base" else [0.35, 0.35, 0.30] for sc in macro_scenarios],
)

service_dette = clip_series(
    out["montant_pret"] / clip_series(out["duree_mois"] / 12, 0.5, None)
    + out["montant_pret"] * annual_rate,
    1000,
    None,
)
out["service_dette_annuel"] = np.round(service_dette, 2)

cashflow_op = clip_series(
    out["ebitda"] * (0.70 + 0.35 * latent_quality) + rng.normal(0, 40000, n), -150000, None
)
out["cashflow_operationnel"] = np.round(cashflow_op, 2)
out["cashflow_libre"] = np.round(
    out["cashflow_operationnel"] - 0.12 * out["montant_total_investissement"] + rng.normal(0, 20000, n),
    2,
)
out["cashflow_cumule"] = np.round(
    out["cashflow_operationnel"] * np.maximum(out["duree_mois"] / 12, 1), 2
)
out["montant_subventionne"] = np.round(
    np.where(rng.random(n) < (0.10 + 0.18 * latent_quality), out["montant_total_investissement"] * (0.05 + 0.20 * rng.random(n)), 0),
    2,
)

# Derived ratios
out["ratio_fdr_bfr"] = np.round(out["fdr"] / clip_series(out["bfr"], 1, None), 4)
out["ratio_liquidite_generale"] = np.round(out["actifs_courants"] / clip_series(out["passifs_courants"], 1, None), 4)
inventory = clip_series(out["chiffre_affaires_annuel"] * (0.03 + 0.10 * latent_risk), 0, None)
out["stock"] = np.round(inventory, 2)
out["quick_ratio"] = np.round(
    (out["actifs_courants"] - out["stock"]) / clip_series(out["passifs_courants"], 1, None),
    4,
)
out["debt_to_equity_ratio"] = np.round(
    (out["dettes_court_terme"] + out["dettes_long_terme"]) / clip_series(out["capitaux_propres"], 1, None),
    4,
)
out["dscr"] = np.round(out["cashflow_operationnel"] / clip_series(out["service_dette_annuel"], 1, None), 4)
interets = clip_series(out["montant_pret"] * annual_rate, 1, None)
out["interets_sur_ebitda"] = np.round(interets / clip_series(np.abs(out["ebitda"]), 1, None), 4)
out["garantie_coverage_ratio"] = np.round(out["garantie_valeur"] / clip_series(out["montant_pret"], 1, None), 4)
out["apport_ratio"] = np.round(out["apport_personnel"] / clip_series(out["montant_total_investissement"], 1, None), 4)
out["ratio_cout_credit"] = np.round(out["cout_credit"] / clip_series(out["montant_pret"], 1, None), 4)
out["historique_acces_credit"] = np.round(
    clip_series(40 + 45 * latent_quality + 8 * out["cofinancement"] + rng.normal(0, 8, n), 0, 100),
    2,
)

# Internal BFPME score decomposition proxies
score_factor = out["score_bfpme_global"]
out["score_financier_bfpme"] = np.round(
    clip_series(score_factor * (0.30 + 0.15 * latent_quality) + rng.normal(0, 8, n), 0, 200), 2
)
out["score_business_bfpme"] = np.round(
    clip_series(score_factor * (0.22 + 0.08 * (1 - latent_risk)) + rng.normal(0, 8, n), 0, 200), 2
)
out["score_management_bfpme"] = np.round(
    clip_series(score_factor * (0.18 + 0.08 * latent_quality) + rng.normal(0, 8, n), 0, 200), 2
)
out["score_industrie_bfpme"] = np.round(
    clip_series(score_factor * (0.12 + 0.08 * (1 - out["niveau_risque_sectoriel_projet"] / 100)) + rng.normal(0, 6, n), 0, 200),
    2,
)
out["variation_score_12m"] = np.round(
    clip_series(18 * (latent_quality - 0.5) + rng.normal(0, 8, n), -35, 35), 2
)
out["tendance_score"] = np.select(
    [out["variation_score_12m"] > 5, out["variation_score_12m"] < -5],
    ["amelioration", "degradation"],
    default="stable",
)

# Payment behaviour and bank relationship
dpd_mean = clip_series(
    2 + 75 * latent_risk + 15 * (np.array(macro_scenarios) == "adverse") + 35 * (np.array(macro_scenarios) == "severe") + rng.normal(0, 10, n),
    0,
    180,
)
out["dpd_moyen"] = np.round(dpd_mean, 1)
out["dpd_max_historique"] = np.round(
    clip_series(out["dpd_moyen"] + 10 + 70 * latent_risk + rng.normal(0, 20, n), 0, 360), 1
)
out["frequence_retards"] = np.round(
    clip_series(0.02 + 0.65 * latent_risk + rng.normal(0, 0.08, n), 0, 1), 4
)
out["montant_impayes"] = np.round(
    clip_series(out["montant_pret"] * (0.00 + 0.18 * latent_risk**2) + rng.normal(0, 12000, n), 0, None),
    2,
)
out["respect_echeances"] = np.round(
    100 * clip_series(0.98 - 0.65 * latent_risk + rng.normal(0, 0.05, n), 0, 1),
    2,
)
out["taux_remboursement_ponctuel"] = np.round(
    100 * clip_series(0.97 - 0.60 * latent_risk + rng.normal(0, 0.05, n), 0, 1),
    2,
)
out["reamenagements_dettes"] = clip_series(np.round(4 * latent_risk + rng.normal(0, 0.6, n)).astype(int), 0, 5)
out["nombre_credits_actifs"] = clip_series(np.round(1 + 4 * latent_quality + rng.normal(0, 1, n)).astype(int), 1, 8)
out["utilisation_lignes_credit_pct"] = np.round(
    100 * clip_series(0.20 + 0.70 * latent_risk + rng.normal(0, 0.08, n), 0, 1),
    2,
)
out["decouverts_frequents"] = (rng.random(n) < clip_series(0.05 + 0.65 * latent_risk, 0, 0.95)).astype(int)
out["augmentation_brutale_dettes"] = (rng.random(n) < clip_series(0.04 + 0.50 * latent_risk, 0, 0.90)).astype(int)
out["baisse_depots"] = (rng.random(n) < clip_series(0.06 + 0.45 * latent_risk, 0, 0.85)).astype(int)
out["retrait_liquidites_frequent"] = (rng.random(n) < clip_series(0.05 + 0.40 * latent_risk, 0, 0.80)).astype(int)
out["confiance_institutionnelle"] = np.round(
    clip_series(85 - 65 * latent_risk + rng.normal(0, 8, n), 5, 100),
    2,
)
out["qualite_communication_banque"] = np.round(
    clip_series(4.8 - 3.2 * latent_risk + rng.normal(0, 0.4, n), 1, 5),
    2,
)
out["historique_litiges"] = clip_series(np.round(3 * latent_risk + rng.normal(0, 0.5, n)).astype(int), 0, 4)
out["relation_bancaire"] = np.round(
    clip_series(80 - 50 * latent_risk + 6 * out["nombre_credits_actifs"] + rng.normal(0, 8, n), 0, 100),
    2,
)
out["qualite_gestion_compte"] = np.round(
    clip_series(82 - 55 * latent_risk + rng.normal(0, 7, n), 0, 100),
    2,
)
out["retards_eventuels"] = (out["dpd_max_historique"] > 15).astype(int)
out["historique_paiement"] = np.select(
    [out["dpd_max_historique"] <= 5, out["dpd_max_historique"] <= 30, out["dpd_max_historique"] <= 90],
    ["excellent", "acceptable", "fragile"],
    default="degrade",
)

# Synthetic default logic for binary classification
score_penalty = (200 - clip_series(out["score_bfpme_global"], 0, 200)) / 200
dpd_penalty = clip_series(out["dpd_moyen"] / 90, 0, 2.5)
liquidity_bonus = clip_series(out["ratio_liquidite_generale"], 0, 3) / 3
guarantee_bonus = clip_series(out["garantie_coverage_ratio"], 0, 2.5) / 2.5
dscr_penalty = clip_series((1.2 - out["dscr"]), -2, 2)
macro_penalty = (
    out["risque_pays_region"] / 100 * 0.7
    + out["risque_sectoriel_global"] / 100 * 0.6
    + 0.2 * out["choc_economique"]
)
behavior_penalty = (
    out["frequence_retards"] * 0.9
    + out["reamenagements_dettes"] * 0.10
    + out["augmentation_brutale_dettes"] * 0.25
    + out["baisse_depots"] * 0.20
)

latent_score_default = (
    -2.4
    + 2.5 * score_penalty
    + 1.6 * dpd_penalty
    + 0.9 * clip_series(out["debt_to_equity_ratio"], 0, 4) / 2
    + 1.1 * dscr_penalty
    + 1.0 * macro_penalty
    + 1.1 * behavior_penalty
    - 1.0 * liquidity_bonus
    - 0.9 * guarantee_bonus
    - 0.6 * clip_series(out["taux_remboursement_ponctuel"] / 100, 0, 1)
    - 0.3 * clip_series(out["confiance_institutionnelle"] / 100, 0, 1)
    + rng.normal(0, 0.45, n)
)

out["pd_target"] = np.round(sigmoid(latent_score_default), 6)
out["default_flag"] = (rng.random(n) < out["pd_target"]).astype(int)

# Reorder columns: base identifiers -> BFPME -> new raw -> ratios -> target
front_cols = [
    "dossier_id",
    "code_modele",
    "risk_class",
    "score_bfpme_good",
    "score_bfpme_average",
    "score_bfpme_global",
    "score_bfpme_gap",
    "score_financier_bfpme",
    "score_business_bfpme",
    "score_management_bfpme",
    "score_industrie_bfpme",
    "variation_score_12m",
    "tendance_score",
]

new_cols = [
    "structure_juridique",
    "capital_social",
    "associes_dominants_pct",
    "nombre_employes",
    "chiffre_affaires_annuel",
    "classification_pme",
    "part_marche_estimee_pct",
    "niveau_concurrence_local",
    "dependance_client_unique_pct",
    "existence_dirigeants_multiples",
    "experience_dirigeant_principal",
    "turnover_direction_3ans",
    "zone_localisation",
    "acces_infrastructures_score",
    "montant_pret",
    "montant_total_investissement",
    "type_credit",
    "duree_credit",
    "duree_mois",
    "cofinancement",
    "credit_rattache",
    "apport_personnel",
    "garantie_type",
    "garantie_valeur",
    "garantie_liquidite",
    "garantie_decote_pct",
    "teg",
    "cout_credit",
    "taux_interet_effectif_reel",
    "frais_annexes",
    "sensibilite_taux",
    "objectif_credit",
    "niveau_risque_sectoriel_projet",
    "capitaux_propres",
    "dettes_court_terme",
    "dettes_long_terme",
    "fdr",
    "bfr",
    "cash_equivalents",
    "actifs_courants",
    "passifs_courants",
    "stock",
    "ebitda",
    "resultat_net",
    "marge_brute_pct",
    "marge_nette_pct",
    "roa_pct",
    "roe_pct",
    "cashflow_operationnel",
    "cashflow_libre",
    "cashflow_cumule",
    "service_dette_annuel",
    "historique_acces_credit",
    "montant_subventionne",
    "qualite_gestion_compte",
    "historique_paiement",
    "retards_eventuels",
    "relation_bancaire",
    "dpd_moyen",
    "dpd_max_historique",
    "frequence_retards",
    "montant_impayes",
    "respect_echeances",
    "taux_remboursement_ponctuel",
    "reamenagements_dettes",
    "nombre_credits_actifs",
    "utilisation_lignes_credit_pct",
    "decouverts_frequents",
    "augmentation_brutale_dettes",
    "baisse_depots",
    "retrait_liquidites_frequent",
    "confiance_institutionnelle",
    "qualite_communication_banque",
    "historique_litiges",
    "scenario_macro",
    "inflation",
    "taux_directeur",
    "croissance_pib",
    "taux_chomage",
    "risque_sectoriel_global",
    "risque_pays_region",
    "choc_economique",
    "ratio_fdr_bfr",
    "ratio_liquidite_generale",
    "quick_ratio",
    "debt_to_equity_ratio",
    "dscr",
    "interets_sur_ebitda",
    "garantie_coverage_ratio",
    "apport_ratio",
    "ratio_cout_credit",
    "pd_target",
    "default_flag",
]

sf_cols = [c for c in out.columns if c.startswith("SF_")]
ordered_cols = front_cols + sf_cols + new_cols
ordered_cols = [c for c in ordered_cols if c in out.columns]
remaining_cols = [c for c in out.columns if c not in ordered_cols]
out = out[ordered_cols + remaining_cols]

out.to_csv(output_path, index=False)

print(f"dataset_final.csv generated: {output_path}")
print(f"Rows: {len(out)}, Columns: {len(out.columns)}")
print(out[["score_bfpme_global", "dpd_moyen", "ratio_liquidite_generale", "garantie_coverage_ratio", "pd_target", "default_flag"]].head())
