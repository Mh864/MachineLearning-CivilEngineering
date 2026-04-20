"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Activity, Gauge, ShieldCheck, Wrench } from "lucide-react"
import type { PredictionResponse, StagePredictionResponse, ApiHealthResponse } from "@/lib/api"
import { getHighRiskProbability } from "@/lib/api"
import { formatDischarge } from "@/lib/constants"

interface AnalyticsDashboardProps {
  result: PredictionResponse | null
  stageResult: StagePredictionResponse | null
  dischargeValues: number[]
  apiHealth: ApiHealthResponse | null
}

function fmtPct(v: number): string {
  return `${Math.round(v * 100)}%`
}

function mean(values: number[]): number {
  if (values.length === 0) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
}

function std(values: number[]): number {
  if (values.length < 2) return 0
  const m = mean(values)
  const varSum = values.reduce((acc, v) => acc + (v - m) ** 2, 0)
  return Math.sqrt(varSum / (values.length - 1))
}

function riskLabelFromPrediction(prediction: number): string {
  if (prediction === 2) return "High"
  if (prediction === 1) return "Medium"
  return "Normal"
}

export function AnalyticsDashboard({
  result,
  stageResult,
  dischargeValues,
  apiHealth,
}: AnalyticsDashboardProps) {
  const validDischarge = dischargeValues.filter(Number.isFinite)
  const dischargeMin = validDischarge.length ? Math.min(...validDischarge) : null
  const dischargeMax = validDischarge.length ? Math.max(...validDischarge) : null
  const dischargeAvg = validDischarge.length ? mean(validDischarge) : null
  const dischargeStd = validDischarge.length ? std(validDischarge) : null

  const probs =
    result && typeof result.probability !== "number"
      ? result.probability
      : result
        ? {
            normal: 1 - getHighRiskProbability(result.probability),
            medium: 0,
            high: getHighRiskProbability(result.probability),
          }
        : null

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[#185FA5]" />
            Risk Decomposition
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {result ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Predicted class</span>
                <Badge variant="secondary">{riskLabelFromPrediction(result.prediction)}</Badge>
              </div>
              <div className="space-y-2">
                <div>
                  <div className="mb-1 flex justify-between text-xs">
                    <span>Normal</span>
                    <span>{fmtPct(probs?.normal ?? 0)}</span>
                  </div>
                  <Progress value={(probs?.normal ?? 0) * 100} className="h-2" />
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-xs">
                    <span>Medium</span>
                    <span>{fmtPct(probs?.medium ?? 0)}</span>
                  </div>
                  <Progress value={(probs?.medium ?? 0) * 100} className="h-2" />
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-xs">
                    <span>High</span>
                    <span>{fmtPct(probs?.high ?? 0)}</span>
                  </div>
                  <Progress value={(probs?.high ?? 0) * 100} className="h-2" />
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Run a prediction to view class-wise probabilities.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Activity className="h-4 w-4 text-[#185FA5]" />
            Input Diagnostics
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Min discharge</p>
            <p className="font-semibold">{dischargeMin == null ? "—" : formatDischarge(dischargeMin)}</p>
          </div>
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Max discharge</p>
            <p className="font-semibold">{dischargeMax == null ? "—" : formatDischarge(dischargeMax)}</p>
          </div>
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Mean discharge</p>
            <p className="font-semibold">{dischargeAvg == null ? "—" : formatDischarge(dischargeAvg)}</p>
          </div>
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Volatility (std)</p>
            <p className="font-semibold">{dischargeStd == null ? "—" : dischargeStd.toFixed(1)}</p>
          </div>
          <div className="rounded-md border p-2 col-span-2">
            <p className="text-xs text-muted-foreground">Stage forecast (next day)</p>
            <p className="font-semibold">
              {stageResult ? `${stageResult.predicted_stage_next_day.toFixed(2)} ${stageResult.units}` : "Not available"}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Wrench className="h-4 w-4 text-[#185FA5]" />
            Operational Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Primary model</span>
            <Badge variant={apiHealth?.model_loaded ? "default" : "secondary"}>
              {apiHealth?.model_loaded ? "Loaded" : "Not loaded"}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Stage model</span>
            <Badge variant={apiHealth?.stage_model_loaded ? "default" : "secondary"}>
              {apiHealth?.stage_model_loaded ? "Loaded" : "Not loaded"}
            </Badge>
          </div>
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Artifact</p>
            <p className="truncate font-mono text-xs">{apiHealth?.artifact_path ?? "—"}</p>
          </div>
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Last refresh</p>
            <p className="font-semibold">
              {apiHealth?.last_refresh?.status ? String(apiHealth.last_refresh.status) : "Unknown"}
            </p>
            <p className="text-xs text-muted-foreground">
              {apiHealth?.last_refresh?.finished_at_utc
                ? String(apiHealth.last_refresh.finished_at_utc)
                : "No refresh metadata yet"}
            </p>
          </div>
          <div className="text-xs text-muted-foreground flex items-center gap-1">
            <Gauge className="h-3 w-3" />
            Uptime: {apiHealth?.uptime_seconds != null ? `${apiHealth.uptime_seconds}s` : "—"}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
