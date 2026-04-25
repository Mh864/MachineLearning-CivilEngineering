## Models and hyperparameters (Flood Risk Prediction)

This project trains and serves three models:

- **Flood risk classification (3 classes)**:
  - Baseline: **Logistic Regression** (`models/model.pkl`)
  - Strong model: **LightGBM** (`models/lgbm_model.pkl`)
- **Stage regression (continuous water level)**:
  - **Stage model** (`models/stage_model.pkl`)

This document explains the main parameters/hyperparameters in clear language, aimed at a civil engineering audience.

---

## Training setup (shared across the flood risk classifiers)

### Chronological split (never random)

We split the time series by date (so we never train on “future” data):

- **Train**: 70% of rows (earliest dates)
- **Validation**: 15% (middle dates)
- **Test**: 15% (most recent dates)

**Why chronological split matters:** In real flood prediction, you always predict the future from the past.  
A random split would let the model “cheat” by learning patterns from future conditions that would not be available at prediction time.

### Target variable (what we predict)

The main classification target is **`target_multiclass`**:

- **0 = Normal**: next-day discharge \( \le \) the **75th percentile (p75)** for that river
- **1 = Medium**: next-day discharge between **p75** and **p90**
- **2 = High**: next-day discharge \( > \) the **90th percentile (p90)** for that river (**flood risk**)

**Per-site thresholds:** p75 and p90 are computed **per gauge station**, using that station’s historical discharge distribution. This makes the classes meaningful for each river.

### Per-site thresholds (reference values)

These values are computed by the pipeline from real USGS history. Listed here as a reference:

- Potomac (`01646500`): p75 `14,200`, p90 `28,540` ft³/s
- Neuse (`02087500`): p75 `1,710`, p90 `3,508` ft³/s
- Allegheny (`03015500`): p75 `748`, p90 `1,450` ft³/s
- Red River (`05054000`): p75 `2,040`, p90 `4,060` ft³/s
- Cherry Creek (`06710247`): p75 `93`, p90 `211` ft³/s
- Trinity (`08066500`): p75 `14,000`, p90 `31,913` ft³/s
- Colorado (`09380000`): p75 `12,600`, p90 `14,600` ft³/s
- Sacramento (`11425500`): p75 `17,500`, p90 `34,380` ft³/s
- Clark Fork (`12301933`): p75 `12,900`, p90 `20,000` ft³/s
- Willamette (`14211720`): p75 `34,800`, p90 `63,640` ft³/s

---

## Features used by the flood risk classifiers (38 total)

The classifiers use **38 feature columns** engineered from the most recent 7 days of discharge and NOAA weather inputs.

### Discharge autoregressive features (10)

- `discharge_lag1`, `discharge_lag2`, `discharge_lag3`
- `discharge_roll_mean_3`, `discharge_roll_mean_7`
- `discharge_roll_std_3`, `discharge_roll_std_7`
- `discharge_roll_max_3`, `discharge_roll_max_7`
- `discharge_diff_1`

### Normalized discharge (per-site relative levels) (8)

These make discharge comparable across rivers. For example, **230 ft³/s** can be “very low” for one river and “flooding” for another.

- `discharge_norm_median` = discharge / (site median discharge)
- `discharge_lag1_norm` = `discharge_lag1` / (site median)
- `discharge_lag2_norm` = `discharge_lag2` / (site median)
- `discharge_lag3_norm` = `discharge_lag3` / (site median)
- `discharge_roll_mean_3_norm` = `discharge_roll_mean_3` / (site median)
- `discharge_roll_mean_7_norm` = `discharge_roll_mean_7` / (site median)
- `discharge_pct_of_p75` = discharge / (site p75)
- `discharge_pct_of_p90` = discharge / (site p90)

### Seasonality (2)

- `month_sin`, `month_cos`  
These let the model represent the seasonal cycle smoothly (e.g., spring melt, rainy seasons) without treating months as unrelated categories.

### Precipitation (11)

- `prcp_lag1`, `prcp_lag2`, `prcp_lag3`
- `prcp_roll_sum_3`, `prcp_roll_sum_7`
- `prcp_roll_mean_3`, `prcp_roll_mean_7`
- `heavy_rain_flag_1d`
- `days_since_last_heavy_rain`
- `prcp_x_discharge_lag1`
- `prcp_roll_sum_3_x_discharge_roll_mean_3`

### Weather (7)

- `tmax`, `tmin`, `tavg`, `temp_range`
- `awnd`, `snow`, `snow_depth`

---

## Model 1 — Logistic Regression (Baseline)

- **File**: `models/model.pkl`
- **Trained in**: `modeling/train.py`
- **Model**: `sklearn.linear_model.LogisticRegression`

Logistic regression is a strong, interpretable baseline for tabular data. It learns a set of weights for the features and outputs class probabilities.

### Hyperparameters used

- **`max_iter=5000`**
  - Maximum number of iterations the solver can use to converge.
  - We use 5000 because the feature set and multi-site dataset can require more iterations to find stable weights.

- **`class_weight="balanced"`**
  - Automatically increases the importance of rare classes (especially high-risk flood days).
  - Without balancing, the model can “play it safe” by predicting normal too often, because floods are less frequent.

- **`multi_class="multinomial"`**
  - Trains one model to predict all 3 classes together (normal/medium/high).
  - This is the standard approach for a true 3-class problem.

- **`solver="lbfgs"`** (default)
  - The numerical optimization method used to fit the model weights.

### Pipeline wrapper

- **`StandardScaler`**
  - Scales all feature columns to comparable numeric ranges before training.
  - This matters because different inputs have different units and magnitudes (e.g., discharge in ft³/s vs precipitation in mm).

### Probability calibration

After training, the saved artifact includes **probability calibration** using **isotonic regression** on the validation slice (when possible).  
Calibration improves how “probability-like” the outputs are (so a 0.60 flood probability behaves more like a real 60% frequency over many examples).

---

## Model 2 — LightGBM (Strong Model)

- **File**: `models/lgbm_model.pkl`
- **Trained in**: `modeling/train.py`
- **Model**: `lightgbm.LGBMClassifier`

LightGBM is a gradient-boosted tree model. It builds many small decision trees; each new tree focuses on correcting errors made by earlier trees.

### Hyperparameters used

- **`n_estimators=300`**
  - Number of trees built.
  - 300 trees is a balance between accuracy and training time.

- **`learning_rate=0.05`**
  - How much each new tree updates (corrects) the overall model.
  - Smaller values are more conservative and can reduce overfitting.

- **`num_leaves=31`**
  - Controls how complex each individual tree can be.
  - More leaves can capture more patterns but can overfit if too large.

- **`class_weight="balanced"`**
  - Same idea as logistic regression: increases attention to rare flood/high-risk cases.

- **`objective="multiclass"`**
  - Tells LightGBM this is a 3-class classification problem.

- **`num_class=3`**
  - Number of output classes: 0 (normal), 1 (medium), 2 (high).

- **`random_state=42`**
  - Fixes the random seed so results are reproducible.
  - This helps when comparing experiments: everyone can retrain and get consistent results.

- **`n_jobs=-1`**
  - Uses all available CPU cores to speed up training.

### Probability calibration

Same as logistic regression: isotonic regression on the validation slice (when possible), stored inside the saved model artifact.

---

## Model 3 — Stage regression model (River height)

- **File**: `models/stage_model.pkl`
- **Purpose**: Predicts **next-day river stage (height)** in **feet**

This is a **regression** model, not a classification model:

- **Classification** predicts categories (Normal / Medium / High).
- **Regression** predicts a continuous value (for example: **12.4 ft**).

The stage model uses a similar “recent history + weather” idea, but its target is **river height** rather than flood risk class. The flood-risk models and stage model can be used together in the dashboard: one gives risk probabilities, the other gives a next-day height estimate.

