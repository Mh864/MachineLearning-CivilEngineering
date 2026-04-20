"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import {
  getRiskLevel,
  getRiskConfig,
  formatDischarge,
  type Station,
} from "@/lib/constants"
import {
  formatModelProbabilityDisplay,
  getHighRiskProbability,
  getTrend,
  type PredictionResponse,
  type StagePredictionResponse,
} from "@/lib/api"
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Droplets,
  Calendar,
  Activity,
  BarChart3,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface ResultPanelProps {
  result: PredictionResponse | null
  stageResult: StagePredictionResponse | null
  dischargeValues: number[]
  station: Station
}

export function ResultPanel({ result, stageResult, dischargeValues, station }: ResultPanelProps) {
  if (!result) {
    return (
      <Card className="h-fit">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5 text-[#185FA5]" />
            Prediction Results
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Droplets className="h-8 w-8 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              Enter discharge values and click predict to see flood risk analysis
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const riskSignal = typeof result.probability === "number" ? result.probability : getHighRiskProbability(result.probability)
  const predictionClass = result.prediction
  const riskLevel =
    typeof result.probability === "number"
      ? getRiskLevel(riskSignal)
      : predictionClass === 2
        ? "high"
        : predictionClass === 1
          ? "medium"
          : "low"
  const riskConfig = getRiskConfig(riskLevel)
  const trend = getTrend(dischargeValues)
  const { barValue, headline: probabilityHeadline } =
    formatModelProbabilityDisplay(result.probability, result.prediction)

  const currentDischarge = dischargeValues[dischargeValues.length - 1] || 0
  const avgDischarge =
    dischargeValues.reduce((a, b) => a + b, 0) / dischargeValues.length

  const trendIconConfig = {
    rising: { icon: TrendingUp, color: "text-amber-600" },
    falling: { icon: TrendingDown, color: "text-emerald-600" },
    stable: { icon: Minus, color: "text-muted-foreground" },
  } as const

  function trendNarrative(): { text: string; color: string } {
    const base = trendIconConfig[trend]
    if (trend === "rising") {
      if (riskLevel === "low" && predictionClass === 0) {
        return {
          text: "Discharge is rising over the last few days, but the model still estimates a low chance of exceeding the high-flow threshold tomorrow.",
          color: "text-muted-foreground",
        }
      }
      if (riskLevel === "high" || predictionClass >= 1) {
        return {
          text: "Discharge is rising and the model indicates elevated flood risk for tomorrow.",
          color: "text-amber-600",
        }
      }
      return {
        text: "Discharge is rising; the model shows moderate flood risk for tomorrow.",
        color: "text-amber-600",
      }
    }
    if (trend === "falling") {
      return {
        text: "Discharge is falling — flood risk is typically lower when the river is receding.",
        color: base.color,
      }
    }
    return {
      text: "Recent discharge is relatively flat compared to the prior few days.",
      color: base.color,
    }
  }

  const trendLine = trendNarrative()
  const TrendIcon = trendIconConfig[trend].icon

  return (
    <Card className="h-fit">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <BarChart3 className="h-5 w-5 text-[#185FA5]" />
          Prediction Results
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Risk Badge */}
        <div
          className={cn(
            "rounded-lg border p-4",
            riskConfig.bgLight,
            riskConfig.borderColor
          )}
        >
          <div className="flex items-center justify-between mb-3">
            <Badge
              className={cn(
                "text-white font-semibold px-3 py-1",
                riskConfig.color
              )}
            >
              {riskConfig.label}
            </Badge>
            <span className="text-sm text-muted-foreground">{station.name}</span>
          </div>

          {/* Large probability number */}
          <div className="text-center mb-3">
            <span
              className={cn("text-5xl font-bold tabular-nums", riskConfig.textColor)}
            >
              {probabilityHeadline}
            </span>
            <p className="text-sm text-muted-foreground mt-1">
              {typeof result.probability === "number" ? "flood probability tomorrow" : "selected risk-class probability"}
            </p>
          </div>

          {/* Animated progress bar */}
          <div className="space-y-1.5">
            <Progress
              value={barValue}
              className={cn(
                "h-3",
                riskLevel === "low" && "[&>[data-slot=progress-indicator]]:bg-emerald-500",
                riskLevel === "medium" && "[&>[data-slot=progress-indicator]]:bg-amber-500",
                riskLevel === "high" && "[&>[data-slot=progress-indicator]]:bg-red-500"
              )}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>0%</span>
              <span>35%</span>
              <span>60%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        {/* Trend insight */}
        <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-3">
          <TrendIcon className={cn("h-5 w-5 shrink-0 mt-0.5", trendLine.color)} />
          <span className={cn("text-sm font-medium leading-snug", trendLine.color)}>
            {trendLine.text}
          </span>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border bg-card p-3 text-center">
            <Activity className="h-4 w-4 text-[#185FA5] mx-auto mb-1" />
            <p className="text-lg font-semibold">{formatDischarge(currentDischarge)}</p>
            <p className="text-xs text-muted-foreground">Current (ft³/s)</p>
          </div>
          <div className="rounded-lg border bg-card p-3 text-center">
            <Calendar className="h-4 w-4 text-[#185FA5] mx-auto mb-1" />
            <p className="text-lg font-semibold">{dischargeValues.length}</p>
            <p className="text-xs text-muted-foreground">Days of data</p>
          </div>
          <div className="rounded-lg border bg-card p-3 text-center">
            <Droplets className="h-4 w-4 text-[#185FA5] mx-auto mb-1" />
            <p className="text-lg font-semibold">{formatDischarge(Math.round(avgDischarge))}</p>
            <p className="text-xs text-muted-foreground">Average (ft³/s)</p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-xs text-center text-muted-foreground pt-2 border-t">
          Powered by LightGBM · 10 US stations
        </p>
        {stageResult && (
          <p className="text-xs text-center text-muted-foreground">
            Next-day stage estimate: {stageResult.predicted_stage_next_day.toFixed(2)} {stageResult.units}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
