export type Station = {
  siteId: string
  name: string
  state: string
}

export const STATIONS: Station[] = [
  { siteId: "01646500", name: "Potomac River at Point of Rocks", state: "MD" },
  { siteId: "02087500", name: "Neuse River near Clayton", state: "NC" },
  { siteId: "03015500", name: "Allegheny River at Eldred", state: "PA" },
  { siteId: "05054000", name: "Red River of the North at Fargo", state: "ND" },
  { siteId: "06710247", name: "Cherry Creek at Denver", state: "CO" },
  { siteId: "08066500", name: "Trinity River at Romayor", state: "TX" },
  { siteId: "09380000", name: "Colorado River near Lees Ferry", state: "AZ" },
  { siteId: "11425500", name: "Sacramento River at Verona", state: "CA" },
  { siteId: "12301933", name: "Clark Fork above Missoula", state: "MT" },
  { siteId: "14211720", name: "Willamette River at Portland", state: "OR" },
]

export const MODEL_RESULTS = {
  logisticRegression: {
    validationF1: 0.438,
    testF1: 0.484,
    testRocAuc: 0.784,
  },
  lightGBM: {
    validationF1: 0.719,
    testF1: 0.746,
    testRocAuc: 0.966,
  },
} as const

export const LEAD_TIME_ANALYSIS = [
  { days: 1, f1: 0.518 },
  { days: 2, f1: 0.488 },
  { days: 3, f1: 0.454 },
  { days: 5, f1: 0.372 },
  { days: 7, f1: 0.352 },
] as const

export type PipelineStep = {
  step: number
  title: string
  description: string
  source?: string
}

export const PIPELINE_STEPS: PipelineStep[] = [
  {
    step: 1,
    title: "USGS discharge",
    description: "Daily gauge discharge time series are collected and aligned to a continuous calendar per site.",
    source: "USGS",
  },
  {
    step: 2,
    title: "NOAA weather merge",
    description: "Precipitation, temperature, wind, and snow fields are joined to each gauge by date.",
    source: "NOAA",
  },
  {
    step: 3,
    title: "Clean & threshold",
    description: "Series are cleaned; a site-specific high-flow threshold defines the next-day binary target.",
  },
  {
    step: 4,
    title: "Feature engineering",
    description: "Lags, rolling statistics, interactions, and calendar features are built for modeling.",
  },
  {
    step: 5,
    title: "Train & evaluate",
    description: "Models are fit on a chronological split and compared with naive baselines and diagnostics.",
  },
  {
    step: 6,
    title: "API & UI",
    description: "The trained artifact serves predictions; the dashboard loads recent windows and calls /predict.",
    source: "FastAPI",
  },
]

export type ModelFeature = { name: string; description: string }

export const MODEL_FEATURES: ModelFeature[] = [
  { name: "discharge_lag1", description: "Prior-day discharge — recent river state without same-day leakage." },
  { name: "discharge_roll_mean_7", description: "Seven-day smoothed flow to capture persistence." },
  { name: "prcp_roll_sum_7", description: "Week-total rainfall context." },
  { name: "heavy_rain_flag_1d", description: "Indicator when daily rain exceeds a site threshold." },
  { name: "tmax / tmin / tavg", description: "Temperature level and derived average for season and melt context." },
  { name: "snow / snow_depth", description: "Daily snowfall and snow depth (filled to zero when missing), aligned with training." },
  { name: "prcp_x_discharge_lag1", description: "Interaction of wet conditions with elevated prior flow." },
]

export type RiskLevel = "low" | "medium" | "high"

export function getRiskLevel(probability: number): RiskLevel {
  if (probability < 0.35) return "low"
  if (probability < 0.6) return "medium"
  return "high"
}

type RiskConfig = {
  label: string
  color: string
  textColor: string
  bgLight: string
  borderColor: string
}

export function getRiskConfig(level: RiskLevel): RiskConfig {
  switch (level) {
    case "low":
      return {
        label: "Low risk",
        color: "bg-emerald-600",
        textColor: "text-emerald-700",
        bgLight: "bg-emerald-50/80",
        borderColor: "border-emerald-200",
      }
    case "medium":
      return {
        label: "Moderate risk",
        color: "bg-amber-500",
        textColor: "text-amber-700",
        bgLight: "bg-amber-50/80",
        borderColor: "border-amber-200",
      }
    case "high":
      return {
        label: "High risk",
        color: "bg-red-600",
        textColor: "text-red-700",
        bgLight: "bg-red-50/80",
        borderColor: "border-red-200",
      }
  }
}

export function formatDischarge(value: number): string {
  if (!Number.isFinite(value)) return "—"
  return Math.round(value).toLocaleString("en-US")
}
