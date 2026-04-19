"use client"

import { format, parseISO } from "date-fns"
import { Input } from "@/components/ui/input"

const N = 7

export type FeatureField =
  | "discharge"
  | "prcp"
  | "tmax"
  | "tmin"
  | "awnd"
  | "snow"
  | "snow_depth"

type SevenDayInputsProps = {
  dates: string[] | null
  discharge: number[]
  prcp: number[]
  tmax: number[]
  tmin: number[]
  awnd: number[]
  snow: number[]
  snow_depth: number[]
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

/** Compact centered field — not full column width */
const numericInputClassName =
  "h-8 w-[5.25rem] max-w-full shrink-0 text-center text-xs font-mono tabular-nums px-1.5"

export function SevenDayInputs({
  dates,
  discharge,
  prcp,
  tmax,
  tmin,
  awnd,
  snow,
  snow_depth,
  onCellChange,
  disabled,
  weatherHint,
}: SevenDayInputsProps) {
  const cols = Array.from({ length: N }, (_, i) => i)

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground leading-relaxed">
        Seven consecutive calendar days, <strong>oldest → newest</strong> (left to right). USGS discharge
        and NOAA daily fields (precip, temperatures, wind, snow) are passed to the model when all seven
        values in a series are filled; otherwise missing series are omitted from the request.
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

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
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
                    className={numericInputClassName}
                    aria-label={`Discharge day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Daily mean discharge (USGS), ft³/s
                </p>
              </div>

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
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
                    className={numericInputClassName}
                    aria-label={`Precipitation day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Daily precipitation (NOAA), mm/day
                </p>
              </div>

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
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
                    className={numericInputClassName}
                    aria-label={`Tmax day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Daily max temperature (NOAA), °C
                </p>
              </div>

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
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
                    className={numericInputClassName}
                    aria-label={`Tmin day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Daily min temperature (NOAA), °C
                </p>
              </div>

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
                  <Input
                    type="number"
                    step="any"
                    inputMode="decimal"
                    disabled={disabled}
                    value={numInputValue(awnd[i] ?? NaN)}
                    onChange={(e) => {
                      const raw = e.target.value
                      const v = raw === "" ? NaN : Number.parseFloat(raw)
                      onCellChange("awnd", i, v)
                    }}
                    className={numericInputClassName}
                    aria-label={`Mean wind speed day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Daily mean wind (NOAA AWND), m/s
                </p>
              </div>

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
                  <Input
                    type="number"
                    step="any"
                    inputMode="decimal"
                    disabled={disabled}
                    value={numInputValue(snow[i] ?? NaN)}
                    onChange={(e) => {
                      const raw = e.target.value
                      const v = raw === "" ? NaN : Number.parseFloat(raw)
                      onCellChange("snow", i, v)
                    }}
                    className={numericInputClassName}
                    aria-label={`Snowfall day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Daily snowfall (NOAA SNOW), mm
                </p>
              </div>

              <div className="flex flex-col items-center gap-1">
                <div className="flex w-full justify-center">
                  <Input
                    type="number"
                    step="any"
                    inputMode="decimal"
                    disabled={disabled}
                    value={numInputValue(snow_depth[i] ?? NaN)}
                    onChange={(e) => {
                      const raw = e.target.value
                      const v = raw === "" ? NaN : Number.parseFloat(raw)
                      onCellChange("snow_depth", i, v)
                    }}
                    className={numericInputClassName}
                    aria-label={`Snow depth day ${i + 1}`}
                  />
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground text-center px-0.5 max-w-[8.5rem]">
                  Snow depth on ground (NOAA SNWD), mm
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
