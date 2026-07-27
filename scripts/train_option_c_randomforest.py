"""
Train Option C RandomForest on data/final_dataset.csv (aligned with notebook Option C).

This is the deployed model for the backend + dashboard. It mirrors
train_option_c_xgboost.py exactly, only swapping the estimator (RandomForest
instead of XGBoost) so inference + sample payloads stay compatible:
- Engineered ratios (debt_total, cash_to_debt, etc.) are columns in allowed_columns.
- SF_* columns and extra BFPME scores are excluded (Hybrid Option C).

Run:
  python scripts\\train_option_c_randomforest.py

After saving, restart the API so joblib reloads (--reload alone may not reload if only data changed).
"""
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler


class Winsorizer(BaseEstimator, TransformerMixin):
    def __init__(self, lower_quantile=0.01, upper_quantile=0.99):
        self.lower_quantile = lower_quantile
        self.upper_quantile = upper_quantile
        self.lower_bounds_ = None
        self.upper_bounds_ = None

    def fit(self, X, y=None):
        X_df = pd.DataFrame(X)
        self.lower_bounds_ = X_df.quantile(self.lower_quantile)
        self.upper_bounds_ = X_df.quantile(self.upper_quantile)
        return self

    def transform(self, X):
        X_df = pd.DataFrame(X).copy()
        return X_df.clip(self.lower_bounds_, self.upper_bounds_, axis=1).values


def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["debt_total"] = out["dettes_court_terme"] + out["dettes_long_terme"]
    out["loan_to_revenue"] = out["montant_pret"] / out["chiffre_affaires_annuel"].replace(0, np.nan)
    out["cash_to_debt"] = out["tresorerie_disponible"] / out["debt_total"].replace(0, np.nan)
    out["financement_externe_intensity"] = out["ratio_financement_externe_projet"]
    out["impayes_to_loan"] = out["montant_impayes"] / out["montant_pret"].replace(0, np.nan)
    out["payment_stress_index"] = (
        np.clip(out["retards_paiement_jours_moyen"] / 90, 0, 3) + np.clip(out["impayes_to_loan"], 0, 3)
    )
    out["fdr_bfr_pressure"] = out["besoin_fonds_roulement_bfr"] / out["fonds_roulement_fdr"].replace(0, np.nan)
    out["garantie_to_loan"] = out["valeur_garanties"] / out["montant_pret"].replace(0, np.nan)
    return out.replace([np.inf, -np.inf], np.nan)


def main():
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"

    df = pd.read_csv(data_dir / "final_dataset.csv")
    target_col = "default_flag"
    df = apply_feature_engineering(df)

    bfpme_drop = [
        "score_bfpme_good",
        "score_bfpme_average",
        "score_bfpme_gap",
        "score_bfpme_global_operational",
        "score_financier",
        "score_business",
        "score_management",
        "score_secteur_industrie",
    ] + [c for c in df.columns if c.startswith("SF_")]
    drop_cols = ["dossier_id", "pd_target"] + bfpme_drop
    drop_cols = [c for c in drop_cols if c in df.columns]

    X = df.drop(columns=drop_cols + [target_col]).copy()
    y = df[target_col].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    allowed_cols = list(X_train.columns)

    ordinal_map = {
        "duree_credit": ["court_terme", "moyen_terme", "long_terme"],
        "score_global_interne": ["Average Financial", "Good Financial"],
    }
    ordinal_features = [c for c in ordinal_map if c in X_train.columns]
    ordinal_categories = [ordinal_map[c] for c in ordinal_features]

    nominal_features = [
        "risk_class",
        "secteur_activite",
        "region_localisation",
        "structure_juridique",
        "classification_pme",
        "zone_localisation",
        "type_credit",
        "objectif_financement",
        "type_taux",
        "scenario_economique",
    ]
    nominal_features = [c for c in nominal_features if c in X_train.columns]

    numeric_features = [c for c in X_train.select_dtypes(include=[np.number]).columns if c not in ordinal_features]

    winsor_cols = [
        "montant_pret",
        "montant_total_investissement",
        "valeur_garanties",
        "chiffre_affaires_annuel",
        "total_actif",
        "total_passif",
        "capitaux_propres",
        "dettes_court_terme",
        "dettes_long_terme",
        "fonds_roulement_fdr",
        "besoin_fonds_roulement_bfr",
        "tresorerie_disponible",
        "montant_impayes",
        "loan_to_revenue",
        "cash_to_debt",
        "impayes_to_loan",
        "fdr_bfr_pressure",
        "garantie_to_loan",
    ]
    winsor_numeric_features = [c for c in winsor_cols if c in numeric_features]
    plain_numeric_features = [c for c in numeric_features if c not in winsor_numeric_features]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "winsor_num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("winsorizer", Winsorizer()),
                        ("scaler", StandardScaler()),
                    ]
                ),
                winsor_numeric_features,
            ),
            (
                "plain_num",
                Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
                plain_numeric_features,
            ),
            (
                "ord",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OrdinalEncoder(
                                categories=ordinal_categories,
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                            ),
                        ),
                    ]
                ),
                ordinal_features,
            ),
            (
                "nom",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                nominal_features,
            ),
        ]
    )

    X_train_p = preprocessor.fit_transform(X_train)
    X_test_p = preprocessor.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=400,
        min_samples_split=8,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_p, y_train)

    y_pred = model.predict(X_test_p)
    y_prob = model.predict_proba(X_test_p)[:, 1]
    metrics = {
        "model_version": "option_c_rf_final_dataset_v2",
        "data_source": "final_dataset.csv",
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "auc": float(roc_auc_score(y_test, y_prob)),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "n_features_raw": int(X_train.shape[1]),
        "n_features_processed": int(X_train_p.shape[1]),
        "allowed_columns_sample": allowed_cols[:12],
        "allowed_columns_count": len(allowed_cols),
    }

    artifact = {
        "model_name": "OptionC_RandomForest_final_dataset",
        "preprocessor": preprocessor,
        "model": model,
        "allowed_columns": allowed_cols,
    }
    joblib_path = data_dir / "option_c_randomforest_model.joblib"
    metrics_path = data_dir / "option_c_randomforest_metrics.json"
    joblib.dump(artifact, joblib_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Saved model: {joblib_path}")
    print(f"Saved metrics: {metrics_path}")
    print(f"Allowed columns ({len(allowed_cols)}): first 15 = {allowed_cols[:15]}")
    print(metrics)


if __name__ == "__main__":
    main()
