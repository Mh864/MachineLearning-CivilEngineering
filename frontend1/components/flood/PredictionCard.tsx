"use client"

import { format, getYear, isValid as isValidDate, parse, parseISO } from "date-fns"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { StationSelector } from "./StationSelector"
import { SevenDayInputs, type FeatureField } from "./SevenDayInputs"
import type { Station } from "@/lib/constants"
import { AlertCircle, Calendar as CalendarIcon, Loader2, Waves } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

function formatWindowEndLong(iso: string | null): string | null {
  if (!iso) return null
  try {
    return format(parseISO(iso), "EEEE, MMMM d, yyyy")
  } catch {
    return null
  }
}

interface PredictionCardProps {
  selectedStation: Station
  onStationChange: (station: Station) => void
  windowDates: string[] | null
  discharge: number[]
  prcp: number[]
  tmax: number[]
  tmin: number[]
  awnd: number[]
  snow: number[]
  snow_depth: number[]
  onSeriesCellChange: (field: FeatureField, index: number, value: number) => void
  weatherHint: string | null
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

function countFiniteDischarge(arr: number[]): number {
  return arr.filter((n) => Number.isFinite(n)).length
}

export function PredictionCard({
  selectedStation,
  onStationChange,
  windowDates,
  discharge,
  prcp,
  tmax,
  tmin,
  awnd,
  snow,
  snow_depth,
  onSeriesCellChange,
  weatherHint,
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
  const valueCount = countFiniteDischarge(discharge)
  const isSeriesValid = discharge.length >= 7 && discharge.slice(0, 7).every((n) => Number.isFinite(n))
  const windowEndLong = formatWindowEndLong(windowEndDate)

  const windowEndTyped = useMemo(() => {
    if (!windowEndDate) return ""
    try {
      return format(parseISO(windowEndDate), "MM/dd/yyyy")
    } catch {
      return ""
    }
  }, [windowEndDate])

  const [windowEndInput, setWindowEndInput] = useState(windowEndTyped)
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)

  useEffect(() => {
    setWindowEndInput(windowEndTyped)
  }, [windowEndTyped])

  function commitWindowEndInput(raw: string) {
    const trimmed = raw.trim()
    if (!trimmed) return

    const parsed = parse(trimmed, "MM/dd/yyyy", new Date())
    if (!isValidDate(parsed)) return

    const iso = format(parsed, "yyyy-MM-dd")
    if (dataRangeStart && iso < dataRangeStart) return
    if (dataRangeEnd && iso > dataRangeEnd) return

    onWindowEndDateChange(iso)
  }

  return (
    <Card className="h-fit">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Waves className="h-5 w-5 text-[#185FA5]" />
          Input Data
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {latestError ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {latestError}
          </div>
        ) : null}

        <div className="flex w-full flex-row items-start gap-4 sm:gap-6">
          <div className="min-w-0 basis-0 flex-1 space-y-2">
            <StationSelector
              selectedStation={selectedStation}
              onSelect={onStationChange}
              latestLoading={latestLoading}
            />
            {autofillLabel && !latestError ? (
              <p className="text-left text-xs text-muted-foreground">{autofillLabel}</p>
            ) : null}
          </div>

          {dataRangeStart && dataRangeEnd && !latestError ? (
            <div className="min-w-0 basis-0 flex-1 space-y-2">
              <label
                htmlFor="window-end-date"
                className="block text-left text-sm font-medium text-foreground"
              >
                End of 7-day window
              </label>
              <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                <div className="relative w-full">
                  <Input
                    id="window-end-date"
                    aria-label="End of 7-day window (MM/DD/YYYY)"
                    inputMode="numeric"
                    placeholder="MM/DD/YYYY"
                    value={windowEndInput}
                    onChange={(e) => setWindowEndInput(e.target.value)}
                    onBlur={(e) => commitWindowEndInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        commitWindowEndInput((e.target as HTMLInputElement).value)
                        ;(e.target as HTMLInputElement).blur()
                      }
                    }}
                    disabled={latestLoading}
                    className="h-9 w-full min-w-0 pr-10 font-mono text-sm"
                  />

                  <PopoverTrigger asChild>
                    <button
                      type="button"
                      aria-label="Open calendar"
                      disabled={latestLoading}
                      className="absolute right-1 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
                    >
                      <CalendarIcon className="h-4 w-4" />
                    </button>
                  </PopoverTrigger>
                </div>

                <PopoverContent className="w-auto p-0" align="end">
                  <Calendar
                    mode="single"
                    captionLayout="dropdown"
                    fromYear={2018}
                    toYear={2024}
                    selected={windowEndDate ? parseISO(windowEndDate) : undefined}
                    onSelect={(d) => {
                      if (!d) return
                      const iso = format(d, "yyyy-MM-dd")
                      if (dataRangeStart && iso < dataRangeStart) return
                      if (dataRangeEnd && iso > dataRangeEnd) return
                      onWindowEndDateChange(iso)
                      setWindowEndInput(format(d, "MM/dd/yyyy"))
                      setIsCalendarOpen(false)
                    }}
                    disabled={(d) => {
                      const iso = format(d, "yyyy-MM-dd")
                      if (dataRangeStart && iso < dataRangeStart) return true
                      if (dataRangeEnd && iso > dataRangeEnd) return true
                      const y = getYear(d)
                      if (y > 2024) return true
                      return false
                    }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <p className="text-left text-xs text-muted-foreground">
                USGS data available {dataRangeStart} → {dataRangeEnd}. The chart uses the seven days
                ending on this date.
              </p>
            </div>
          ) : null}
        </div>

        {windowEndLong && !latestError ? (
          <div className="rounded-lg border border-border bg-muted/30 px-4 py-4 text-center">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Window ends on
            </p>
            <p className="mt-1 text-lg font-semibold text-foreground sm:text-xl">
              {windowEndLong}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground tabular-nums">
              {windowEndDate}
            </p>
          </div>
        ) : null}

        <SevenDayInputs
          dates={windowDates}
          discharge={discharge}
          prcp={prcp}
          tmax={tmax}
          tmin={tmin}
          awnd={awnd}
          snow={snow}
          snow_depth={snow_depth}
          onCellChange={onSeriesCellChange}
            disabled={latestLoading}
            weatherHint={weatherHint}
        />

        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            Discharge: {valueCount} / 7 days filled
          </span>
          {valueCount > 0 && valueCount < 7 && (
            <span className="text-amber-600 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              Enter all 7 discharge values
            </span>
          )}
          {isSeriesValid && (
            <span className="text-emerald-600">Ready to predict</span>
          )}
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
          disabled={!isSeriesValid || isLoading || latestLoading}
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
