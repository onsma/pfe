import numpy as np
import pandas as pd


def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if {"dettes_court_terme", "dettes_long_terme"}.issubset(out.columns):
        out["debt_total"] = out["dettes_court_terme"] + out["dettes_long_terme"]
    if {"montant_pret", "chiffre_affaires_annuel"}.issubset(out.columns):
        out["loan_to_revenue"] = out["montant_pret"] / out["chiffre_affaires_annuel"].replace(0, np.nan)
    if {"tresorerie_disponible", "debt_total"}.issubset(out.columns):
        out["cash_to_debt"] = out["tresorerie_disponible"] / out["debt_total"].replace(0, np.nan)
    if "ratio_financement_externe_projet" in out.columns:
        out["financement_externe_intensity"] = out["ratio_financement_externe_projet"]
    if {"montant_impayes", "montant_pret"}.issubset(out.columns):
        out["impayes_to_loan"] = out["montant_impayes"] / out["montant_pret"].replace(0, np.nan)
    if {"retards_paiement_jours_moyen", "impayes_to_loan"}.issubset(out.columns):
        out["payment_stress_index"] = np.clip(out["retards_paiement_jours_moyen"] / 90, 0, 3) + np.clip(
            out["impayes_to_loan"], 0, 3
        )
    if {"besoin_fonds_roulement_bfr", "fonds_roulement_fdr"}.issubset(out.columns):
        out["fdr_bfr_pressure"] = out["besoin_fonds_roulement_bfr"] / out["fonds_roulement_fdr"].replace(0, np.nan)
    if {"valeur_garanties", "montant_pret"}.issubset(out.columns):
        out["garantie_to_loan"] = out["valeur_garanties"] / out["montant_pret"].replace(0, np.nan)

    return out.replace([np.inf, -np.inf], np.nan)

