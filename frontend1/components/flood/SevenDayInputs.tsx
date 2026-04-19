"use client"

import { format, parseISO } from "date-fns"
import { Input } from "@/components/ui/input"

const N = 7

export type FeatureField = "discharge" | "prcp" | "tmax" | "tmin"

type SevenDayInputsProps = {
  dates: string[] | null
  discharge: number[]
  prcp: number[]
  tmax: number[]
  tmin: number[]
  onCellChange: (field: FeatureField, index: number, value: number) => void
  disabled?: boolean
  weatherHint?: string | null
}

function ColumnDateHeader({ isoDate, fallbackTitle }: { isoDate: string | undefined; fallbackTitle: string }) {
  if (!isoDate) {
    return (
      <div className="text-center border-b border-border pb-2">
        <p className="text-sm font-semibold text-foreground leading-tight">{fallbackTitle}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">Load data or pick an end date</p>
      </div>
    )
  }
  try {
    const d = parseISO(isoDate)
    return (
      <div className="text-center border-b border-border pb-2 space-y-0.5">
        <p className="text-[11px] font-medium text-muted-foreground tabular-nums">
          {format(d, "EEEE")}
        </p>
        <p className="text-sm font-semibold text-foreground leading-snug">
          {format(d, "MMMM d, yyyy")}
        </p>
        <p className="text-[10px] text-muted-foreground font-mono tabular-nums">{isoDate}</p>
      </div>
    )
  } catch {
    return (
      <div className="text-center border-b border-border pb-2">
        <p className="text-sm font-semibold text-foreground">{fallbackTitle}</p>
      </div>
    )
  }
}

function numInputValue(v: number): string {
  return Number.isFinite(v) ? String(v) : ""
}

export function SevenDayInputs({
  dates,
  discharge,
  prcp,
  tmax,
  tmin,
  onCellChange,
  disabled,
  weatherHint,
}: SevenDayInputsProps) {
  const cols = Array.from({ length: N }, (_, i) => i)

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground leading-relaxed">
        Seven consecutive calendar days, <strong>oldest → newest</strong> (left to right). Discharge,
        rain, and temperatures are passed through to the model in that order. Wind and snow
        features from training default to zero when not provided by the API.
      </p>
      {weatherHint ? (
        <p className="text-xs text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-800 rounded-md px-2 py-1.5">
          {weatherHint}
        </p>
      ) : null}

      <div className="overflow-x-auto pb-2 -mx-1 px-1">
        <div
          className="grid gap-3 w-full min-w-[min(100%,900px)]"
          style={{ gridTemplateColumns: `repeat(${N}, minmax(0, 1fr))` }}
        >
          {cols.map((i) => {
            const iso = dates?.[i]
            const fallback =
              i === 0 ? "Oldest day" : i === N - 1 ? "Newest day" : `Day ${i + 1}`
            return (
            <div
              key={i}
              className="flex flex-col gap-3 rounded-lg border bg-card/50 p-2 shadow-sm min-w-0"
            >
              <ColumnDateHeader isoDate={iso} fallbackTitle={fallback} />

              <div className="space-y-1">
                <Input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  disabled={disabled}
                  value={numInputValue(discharge[i] ?? NaN)}
                  onChange={(e) => {
                    const raw = e.target.value
                    const v = raw === "" ? NaN : Number.parseFloat(raw)
                    onCellChange("discharge", i, v)
                  }}
                  className="h-9 font-mono text-sm px-2"
                  aria-label={`Discharge day ${i + 1}`}
                />
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5">
                  Daily mean discharge (USGS), ft³/s
                </p>
              </div>

              <div className="space-y-1">
                <Input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  disabled={disabled}
                  value={numInputValue(prcp[i] ?? NaN)}
                  onChange={(e) => {
                    const raw = e.target.value
                    const v = raw === "" ? NaN : Number.parseFloat(raw)
                    onCellChange("prcp", i, v)
                  }}
                  className="h-9 font-mono text-sm px-2"
                  aria-label={`Precipitation day ${i + 1}`}
                />
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5">
                  Daily precipitation (NOAA), mm/day
                </p>
              </div>

              <div className="space-y-1">
                <Input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  disabled={disabled}
                  value={numInputValue(tmax[i] ?? NaN)}
                  onChange={(e) => {
                    const raw = e.target.value
                    const v = raw === "" ? NaN : Number.parseFloat(raw)
                    onCellChange("tmax", i, v)
                  }}
                  className="h-9 font-mono text-sm px-2"
                  aria-label={`Tmax day ${i + 1}`}
                />
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5">
                  Daily max temperature (NOAA), °C
                </p>
              </div>

              <div className="space-y-1">
                <Input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  disabled={disabled}
                  value={numInputValue(tmin[i] ?? NaN)}
                  onChange={(e) => {
                    const raw = e.target.value
                    const v = raw === "" ? NaN : Number.parseFloat(raw)
                    onCellChange("tmin", i, v)
                  }}
                  className="h-9 font-mono text-sm px-2"
                  aria-label={`Tmin day ${i + 1}`}
                />
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5">
                  Daily min temperature (NOAA), °C
                </p>
              </div>
            </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
