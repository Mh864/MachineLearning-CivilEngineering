"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { StationSelector } from "./StationSelector"
import type { Station } from "@/lib/constants"
import { parseDischargeInput } from "@/lib/api"
import { AlertCircle, Loader2, Waves } from "lucide-react"

interface PredictionCardProps {
  selectedStation: Station
  onStationChange: (station: Station) => void
  dischargeInput: string
  onDischargeChange: (value: string) => void
  onPredict: () => void
  isLoading: boolean
  error: string | null
  latestLoading: boolean
  latestError: string | null
  autofillLabel: string | null
  dataRangeStart: string | null
  dataRangeEnd: string | null
  windowEndDate: string | null
  onWindowEndDateChange: (isoDate: string) => void
}

export function PredictionCard({
  selectedStation,
  onStationChange,
  dischargeInput,
  onDischargeChange,
  onPredict,
  isLoading,
  error,
  latestLoading,
  latestError,
  autofillLabel,
  dataRangeStart,
  dataRangeEnd,
  windowEndDate,
  onWindowEndDateChange,
}: PredictionCardProps) {
  const parsedValues = parseDischargeInput(dischargeInput)
  const valueCount = parsedValues.length
  const isValid = valueCount >= 7

  return (
    <Card className="h-fit">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Waves className="h-5 w-5 text-[#185FA5]" />
          Input Data
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <StationSelector
          selectedStation={selectedStation}
          onSelect={onStationChange}
          latestLoading={latestLoading}
        />

        {latestError ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {latestError}
          </div>
        ) : null}

        {autofillLabel && !latestError ? (
          <p className="text-xs text-muted-foreground">{autofillLabel}</p>
        ) : null}

        {dataRangeStart && dataRangeEnd && !latestError ? (
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              End of 7-day window
            </label>
            <Input
              type="date"
              min={dataRangeStart}
              max={dataRangeEnd}
              value={windowEndDate ?? ""}
              onChange={(e) => {
                const v = e.target.value
                if (v) onWindowEndDateChange(v)
              }}
              disabled={latestLoading}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              USGS data available {dataRangeStart} → {dataRangeEnd}. The chart uses
              the seven days ending on this date.
            </p>
          </div>
        ) : null}

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">
            Recent Discharge Values
          </label>
          <Textarea
            placeholder="Enter 7 or more comma-separated discharge values (ft³/s)&#10;Example: 1200, 1350, 1400, 1280, 1500, 1620, 1580"
            value={dischargeInput}
            onChange={(e) => onDischargeChange(e.target.value)}
            className="min-h-[100px] resize-none font-mono text-sm"
          />
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              {valueCount} value{valueCount !== 1 ? "s" : ""} entered
            </span>
            {valueCount > 0 && valueCount < 7 && (
              <span className="text-amber-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                Need at least 7 values
              </span>
            )}
            {isValid && (
              <span className="text-emerald-600">Ready to predict</span>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        <Button
          onClick={onPredict}
          disabled={!isValid || isLoading || latestLoading}
          className="w-full bg-[#185FA5] hover:bg-[#185FA5]/90 text-white"
          size="lg"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            "Predict Flood Risk"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
