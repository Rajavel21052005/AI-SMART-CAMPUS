# ============================================================
# training/train_risk_model.py — ML Risk Prediction Trainer
# Trains Random Forest, XGBoost, Logistic Regression.
# Auto-selects best model by F1-score and saves to ai_models/.
#
# Usage (from project root, with venv active):
#   python training/train_risk_model.py
#
# Or with synthetic data for testing:
#   python training/train_risk_model.py --synthetic
# ============================================================

import os
import sys
import pickle
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime

# Add project root to path so app can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ── Feature columns ───────────────────────────────────────────
FEATURE_COLS = ['attend_pct', 'avg_marks', 'assign_pct', 'prev_gpa', 'lab_score']
TARGET_COL   = 'risk_label'   # 0=Safe, 1=Moderate, 2=High
LABEL_MAP    = {'Safe': 0, 'Moderate': 1, 'High': 2}
LABEL_NAMES  = ['Safe', 'Moderate', 'High']
MODEL_DIR    = os.path.join(os.path.dirname(__file__), '..', 'ai_models')


def load_data_from_db() -> pd.DataFrame:
    """Pull features from the live database."""
    from app import create_app, db
    from app.models.risk import RiskPrediction, RiskLevel

    app = create_app()
    rows = []
    with app.app_context():
        predictions = RiskPrediction.query.all()
        for p in predictions:
            rows.append({
                'attend_pct': p.attend_pct or 0,
                'avg_marks':  p.avg_marks  or 0,
                'assign_pct': p.assign_pct or 0,
                'prev_gpa':   p.prev_gpa   or 0,
                'lab_score':  p.lab_score  or 0,
                'risk_label': LABEL_MAP.get(p.risk_level.value, 1),
            })
    logger.info(f'Loaded {len(rows)} records from database')
    return pd.DataFrame(rows)


def generate_synthetic_data(n: int = 600) -> pd.DataFrame:
    """
    Generate realistic synthetic student data for demonstration/testing.
    Mirrors real-world distributions:
      - 50% Safe, 30% Moderate, 20% High Risk
    """
    np.random.seed(42)
    rows = []

    for _ in range(n):
        risk = np.random.choice([0, 1, 2], p=[0.50, 0.30, 0.20])

        if risk == 0:      # Safe
            attend  = np.clip(np.random.normal(88, 6),  75, 100)
            marks   = np.clip(np.random.normal(72, 10), 55, 100)
            assign  = np.clip(np.random.normal(90, 8),  70, 100)
            gpa     = np.clip(np.random.normal(7.8, 1), 6,  10)
            lab     = np.clip(np.random.normal(78, 10), 55, 100)
        elif risk == 1:    # Moderate
            attend  = np.clip(np.random.normal(72, 7),  60, 80)
            marks   = np.clip(np.random.normal(54, 10), 35, 68)
            assign  = np.clip(np.random.normal(65, 12), 40, 82)
            gpa     = np.clip(np.random.normal(5.8, 1), 4,  7)
            lab     = np.clip(np.random.normal(60, 12), 35, 78)
        else:              # High Risk
            attend  = np.clip(np.random.normal(54, 10), 30, 68)
            marks   = np.clip(np.random.normal(36, 10), 15, 52)
            assign  = np.clip(np.random.normal(40, 15), 10, 60)
            gpa     = np.clip(np.random.normal(3.8, 1), 1,  5.5)
            lab     = np.clip(np.random.normal(42, 12), 15, 60)

        rows.append({
            'attend_pct': round(attend, 1),
            'avg_marks':  round(marks,  1),
            'assign_pct': round(assign, 1),
            'prev_gpa':   round(gpa,    2),
            'lab_score':  round(lab,    1),
            'risk_label': risk,
        })

    df = pd.DataFrame(rows)
    logger.info(f'Synthetic data: {len(df)} samples | '
                f"Safe={sum(df.risk_label==0)} "
                f"Moderate={sum(df.risk_label==1)} "
                f"High={sum(df.risk_label==2)}")
    return df


def train_and_evaluate(df: pd.DataFrame) -> dict:
    """
    Train three classifiers, compare metrics, return results dict.
    """
    from sklearn.model_selection     import train_test_split, StratifiedKFold, cross_val_score
    from sklearn.preprocessing       import StandardScaler
    from sklearn.linear_model        import LogisticRegression
    from sklearn.ensemble            import RandomForestClassifier
    from sklearn.metrics             import (classification_report,
                                             accuracy_score, f1_score,
                                             confusion_matrix)
    from xgboost import XGBClassifier

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    # ── Train / test split (stratified) ──────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # ── Feature scaling (important for LR) ───────────────────
    scaler  = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # ── Define models ─────────────────────────────────────────
    models = {
        'RandomForest': RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=3,
            class_weight='balanced', random_state=42, n_jobs=-1
        ),
        'XGBoost': XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            use_label_encoder=False, eval_metric='mlogloss',
            random_state=42, verbosity=0
        ),
        'LogisticRegression': LogisticRegression(
            C=1.0, max_iter=1000, class_weight='balanced',
            multi_class='multinomial', solver='lbfgs', random_state=42
        ),
    }

    results     = {}
    best_name   = None
    best_f1     = -1.0
    best_model  = None

    logger.info('\n' + '='*60)
    logger.info('MODEL TRAINING & EVALUATION RESULTS')
    logger.info('='*60)

    for name, model in models.items():
        # Use scaled data for LR, raw for tree models
        Xtr = X_train_s if name == 'LogisticRegression' else X_train
        Xte = X_test_s  if name == 'LogisticRegression' else X_test

        model.fit(Xtr, y_train)
        y_pred = model.predict(Xte)

        acc    = accuracy_score(y_test, y_pred)
        f1     = f1_score(y_test, y_pred, average='weighted')
        report = classification_report(y_test, y_pred, target_names=LABEL_NAMES)

        # 5-fold CV
        cv_scores = cross_val_score(model, Xtr, y_train, cv=5, scoring='f1_weighted')
        cv_mean   = cv_scores.mean()
        cv_std    = cv_scores.std()

        results[name] = {
            'accuracy': round(acc, 4),
            'f1_score': round(f1,  4),
            'cv_mean':  round(cv_mean, 4),
            'cv_std':   round(cv_std,  4),
            'report':   report,
            'confusion': confusion_matrix(y_test, y_pred).tolist(),
        }

        logger.info(f'\n── {name} ──')
        logger.info(f'  Accuracy : {acc:.4f}')
        logger.info(f'  F1-Score : {f1:.4f}')
        logger.info(f'  CV Mean  : {cv_mean:.4f} ± {cv_std:.4f}')
        logger.info(f'\n{report}')

        if f1 > best_f1:
            best_f1   = f1
            best_name = name
            best_model = model

    logger.info('='*60)
    logger.info(f'🏆  Best model: {best_name} (F1={best_f1:.4f})')
    logger.info('='*60)

    return {
        'results':       results,
        'best_model':    best_model,
        'best_name':     best_name,
        'best_f1':       best_f1,
        'scaler':        scaler,
        'feature_cols':  FEATURE_COLS,
        'label_names':   LABEL_NAMES,
        'trained_at':    datetime.utcnow().isoformat(),
        'n_samples':     len(df),
    }


def save_model(training_result: dict):
    """Persist the best model and scaler to disk."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path  = os.path.join(MODEL_DIR, 'risk_model.pkl')
    scaler_path = os.path.join(MODEL_DIR, 'risk_scaler.pkl')
    meta_path   = os.path.join(MODEL_DIR, 'risk_meta.pkl')

    with open(model_path,  'wb') as f: pickle.dump(training_result['best_model'], f)
    with open(scaler_path, 'wb') as f: pickle.dump(training_result['scaler'],     f)

    meta = {k: v for k, v in training_result.items()
            if k not in ('best_model', 'scaler')}
    with open(meta_path, 'wb') as f: pickle.dump(meta, f)

    logger.info(f'Model saved → {model_path}')
    logger.info(f'Scaler saved → {scaler_path}')
    logger.info(f'Metadata saved → {meta_path}')


def print_summary(training_result: dict):
    """Print a clean comparison table."""
    print('\n' + '─'*55)
    print(f"{'Model':<22} {'Accuracy':>10} {'F1-Score':>10} {'CV Mean':>10}")
    print('─'*55)
    for name, res in training_result['results'].items():
        marker = ' ◄ BEST' if name == training_result['best_name'] else ''
        print(f"{name:<22} {res['accuracy']:>10.4f} {res['f1_score']:>10.4f} "
              f"{res['cv_mean']:>10.4f}{marker}")
    print('─'*55)
    print(f"\n✅  Best model: {training_result['best_name']}")
    print(f"   F1-Score:   {training_result['best_f1']:.4f}")
    print(f"   Samples:    {training_result['n_samples']}")
    print(f"   Saved to:   {MODEL_DIR}/\n")


# ── Entry point ───────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train academic risk prediction model')
    parser.add_argument('--synthetic', action='store_true',
                        help='Use synthetic data instead of database')
    parser.add_argument('--n',         type=int, default=600,
                        help='Number of synthetic samples (default 600)')
    args = parser.parse_args()

    logger.info('Starting risk model training…')

    if args.synthetic:
        logger.info('Using synthetic data…')
        df = generate_synthetic_data(n=args.n)
    else:
        logger.info('Loading data from database…')
        df = load_data_from_db()

    if len(df) < 30:
        logger.warning(f'Only {len(df)} records — using synthetic data instead')
        df = generate_synthetic_data(n=600)

    result = train_and_evaluate(df)
    save_model(result)
    print_summary(result)
