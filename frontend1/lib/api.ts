const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")

export type ApiHealthResponse = {
  status: string
  model_loaded: boolean
  artifact_path: string | null
  stage_model_loaded?: boolean
  stage_artifact_path?: string | null
  uptime_seconds?: number
  calibration?: { method?: string; fit_on?: string }
  last_refresh?: {
    status?: string
    finished_at_utc?: string
    duration_seconds?: number
  }
}

export type PredictionResponse = {
  site_id: string
  prediction: number
  probability: number | { normal: number; medium: number; high: number }
  risk_label?: string
}

export type StagePredictionResponse = {
  site_id: string
  predicted_stage_next_day: number
  units: string
}

export type ApiError = Error & { isOffline?: boolean }

export type LatestDataResponse = {
  site_id: string
  dates: string[]
  discharge: number[]
  stage?: Array<number | null>
  stage_available?: boolean
  rainfall_mm: number[]
  rainfall_available: boolean
  tmax_c: number[]
  tmin_c: number[]
  awnd: number[]
  snow: number[]
  snow_depth: number[]
  weather_available: boolean
  latest_date: string
  data_start: string
  data_end: string
}

export async function checkApiStatus(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/health`, { cache: "no-store" })
    if (!r.ok) return false
    const j: { model_loaded?: boolean } = await r.json()
    return j.model_loaded === true
  } catch {
    return false
  }
}

export async function getApiHealth(): Promise<ApiHealthResponse | null> {
  try {
    const r = await fetch(`${API_BASE}/health`, { cache: "no-store" })
    if (!r.ok) return null
    return r.json()
  } catch {
    return null
  }
}

export async function getLatestData(siteId: string, endDate?: string): Promise<LatestDataResponse> {
  const u = new URL(`${API_BASE}/latest`)
  u.searchParams.set("site_id", siteId)
  if (endDate) u.searchParams.set("end_date", endDate)
  const r = await fetch(u.toString(), { cache: "no-store" })
  if (!r.ok) {
    const errBody = await r.json().catch(() => ({}))
    const detail = (errBody as { detail?: unknown }).detail
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? JSON.stringify(detail)
          : r.statusText
    throw new Error(msg)
  }
  return r.json()
}

export type PredictOptions = {
  recentDischarge?: number[]
  recentStage?: number[]
  recentPrcp?: number[]
  recentTmax?: number[]
  recentTmin?: number[]
  recentAwnd?: number[]
  recentSnow?: number[]
  recentSnowDepth?: number[]
  asOfDate?: string
}

export async function getPrediction(
  siteId: string,
  recentDischarge: number[],
  opts: PredictOptions = {}
): Promise<PredictionResponse> {
  const u = new URL(`${API_BASE}/predict`)
  u.searchParams.set("site_id", siteId)
  u.searchParams.set("recent_discharge", recentDischarge.join(","))
  if (opts.asOfDate) u.searchParams.set("as_of_date", opts.asOfDate)
  if (opts.recentPrcp?.length === 7) u.searchParams.set("recent_prcp", opts.recentPrcp.join(","))
  if (opts.recentTmax?.length === 7) u.searchParams.set("tmax", opts.recentTmax.join(","))
  if (opts.recentTmin?.length === 7) u.searchParams.set("tmin", opts.recentTmin.join(","))
  if (opts.recentAwnd?.length === 7) u.searchParams.set("awnd", opts.recentAwnd.join(","))
  if (opts.recentSnow?.length === 7) u.searchParams.set("snow", opts.recentSnow.join(","))
  if (opts.recentSnowDepth?.length === 7) u.searchParams.set("snow_depth", opts.recentSnowDepth.join(","))

  let r: Response
  try {
    r = await fetch(u.toString(), { cache: "no-store" })
  } catch {
    const err = new Error("API unreachable — is the backend running on port 8000?") as ApiError
    err.isOffline = true
    throw err
  }
  if (!r.ok) {
    const errBody = await r.json().catch(() => ({}))
    const detail = (errBody as { detail?: unknown }).detail
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? JSON.stringify(detail)
          : r.statusText
    throw new Error(msg)
  }
  return r.json()
}

export async function getStagePrediction(
  siteId: string,
  recentStage: number[],
  opts: PredictOptions = {}
): Promise<StagePredictionResponse> {
  const u = new URL(`${API_BASE}/predict-stage`)
  u.searchParams.set("site_id", siteId)
  u.searchParams.set("recent_stage", recentStage.join(","))
  if (opts.asOfDate) u.searchParams.set("as_of_date", opts.asOfDate)
  if (opts.recentPrcp?.length === 7) u.searchParams.set("recent_prcp", opts.recentPrcp.join(","))
  if (opts.recentTmax?.length === 7) u.searchParams.set("tmax", opts.recentTmax.join(","))
  if (opts.recentTmin?.length === 7) u.searchParams.set("tmin", opts.recentTmin.join(","))
  if (opts.recentDischarge?.length === 7) u.searchParams.set("recent_discharge", opts.recentDischarge.join(","))

  const r = await fetch(u.toString(), { cache: "no-store" })
  if (!r.ok) {
    const errBody = await r.json().catch(() => ({}))
    const detail = (errBody as { detail?: unknown }).detail
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? JSON.stringify(detail)
          : r.statusText
    throw new Error(msg)
  }
  return r.json()
}

export function getHighRiskProbability(probability: PredictionResponse["probability"]): number {
  if (typeof probability === "number") return probability
  return probability.high
}

export function formatModelProbabilityDisplay(
  probability: PredictionResponse["probability"],
  prediction: number
) {
  const p = typeof probability === "number" ? probability : prediction === 2 ? probability.high : prediction === 1 ? probability.medium : probability.normal
  const pct = Math.round(p * 100)
  const barValue = Math.min(100, Math.max(0, pct))
  return { barValue, headline: `${pct}%` }
}

export function getTrend(values: number[]): "rising" | "falling" | "stable" {
  if (values.length < 2) return "stable"
  const first = values[0]
  const last = values[values.length - 1]
  const delta = last - first
  const threshold = Math.max(Math.abs(first) * 0.02, 1)
  if (delta > threshold) return "rising"
  if (delta < -threshold) return "falling"
  return "stable"
}
