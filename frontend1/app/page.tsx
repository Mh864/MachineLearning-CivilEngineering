"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { format, parseISO } from "date-fns"
import { Header } from "@/components/flood/Header"
import { PredictionCard } from "@/components/flood/PredictionCard"
import type { FeatureField } from "@/components/flood/SevenDayInputs"
import { ResultPanel } from "@/components/flood/ResultPanel"
import { DischargeChart } from "@/components/flood/DischargeChart"
import { AnalyticsDashboard } from "@/components/flood/AnalyticsDashboard"
import { STATIONS, type Station } from "@/lib/constants"
import {
  checkApiStatus,
  getApiHealth,
  getLatestData,
  getPrediction,
  getStagePrediction,
  type PredictionResponse,
  type StagePredictionResponse,
  type ApiError,
  type ApiHealthResponse,
} from "@/lib/api"

function nan7(): number[] {
  return Array.from({ length: 7 }, () => NaN)
}

function ensure7(arr: number[], pad: number): number[] {
  const s = arr.slice(0, 7)
  const out = [...s]
  while (out.length < 7) out.push(pad)
  return out
}

function optionalFinite7(arr: number[]): number[] | undefined {
  const s = arr.slice(0, 7)
  if (s.length < 7) return undefined
  if (!s.every(Number.isFinite)) return undefined
  return s
}

function formatAutofillLabel(dates: string[]): string {
  if (dates.length === 0) return ""
  const first = parseISO(dates[0])
  const last = parseISO(dates[dates.length - 1])
  return `Auto-filled from USGS + NOAA — ${format(first, "MMM d")} to ${format(last, "MMM d, yyyy")}`
}

export default function Dashboard() {
  const [apiStatus, setApiStatus] = useState<boolean | null>(null)
  const [apiHealth, setApiHealth] = useState<ApiHealthResponse | null>(null)
  const [selectedStation, setSelectedStation] = useState<Station>(STATIONS[0])
  const [dischargeSeries, setDischargeSeries] = useState<number[]>(nan7)
  const [prcpSeries, setPrcpSeries] = useState<number[]>(nan7)
  const [stageSeries, setStageSeries] = useState<number[]>(nan7)
  const [tmaxSeries, setTmaxSeries] = useState<number[]>(nan7)
  const [tminSeries, setTminSeries] = useState<number[]>(nan7)
  const [awndSeries, setAwndSeries] = useState<number[]>(nan7)
  const [snowSeries, setSnowSeries] = useState<number[]>(nan7)
  const [snowDepthSeries, setSnowDepthSeries] = useState<number[]>(nan7)
  const [windowDates, setWindowDates] = useState<string[] | null>(null)
  const [weatherMeta, setWeatherMeta] = useState<{
    rainfallAvailable: boolean
    weatherAvailable: boolean
  } | null>(null)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PredictionResponse | null>(null)
  const [stageResult, setStageResult] = useState<StagePredictionResponse | null>(null)
  const [latestLoading, setLatestLoading] = useState(false)
  const [latestError, setLatestError] = useState<string | null>(null)
  const [autofillLabel, setAutofillLabel] = useState<string | null>(null)
  const [dataRangeStart, setDataRangeStart] = useState<string | null>(null)
  const [dataRangeEnd, setDataRangeEnd] = useState<string | null>(null)
  const [seriesAsOfDate, setSeriesAsOfDate] = useState<string | null>(null)

  const weatherHint = useMemo(() => {
    if (!weatherMeta) return null
    if (!weatherMeta.rainfallAvailable && !weatherMeta.weatherAvailable) {
      return "NOAA daily file not matched for this gauge/date window. Precipitation and temperature fields show 0 — the API and training pipeline use the same neutral fill when weather is missing."
    }
    if (!weatherMeta.weatherAvailable) {
      return "NOAA temperature fields were not available for part of this window; values may be 0 °C where the backend filled missing data."
    }
    return null
  }, [weatherMeta])

  const chartDischargeValues = useMemo(() => {
    const d = dischargeSeries.slice(0, 7)
    return d.length === 7 && d.every(Number.isFinite) ? d : []
  }, [dischargeSeries])

  useEffect(() => {
    checkApiStatus().then(setApiStatus)
    getApiHealth().then(setApiHealth)
  }, [])

  const handleSeriesCellChange = useCallback(
    (field: FeatureField, index: number, value: number) => {
      const patch = (prev: number[]) => {
        const n = [...prev]
        while (n.length < 7) n.push(NaN)
        n[index] = value
        return n.slice(0, 7)
      }
      if (field === "discharge") setDischargeSeries(patch)
      else if (field === "prcp") setPrcpSeries(patch)
      else if (field === "tmax") setTmaxSeries(patch)
      else if (field === "tmin") setTminSeries(patch)
      else if (field === "awnd") setAwndSeries(patch)
      else if (field === "snow") setSnowSeries(patch)
      else setSnowDepthSeries(patch)
    },
    []
  )

  const loadLatestForStation = useCallback(
    async (station: Station, endDate?: string) => {
      setLatestLoading(true)
      setLatestError(null)
      setAutofillLabel(null)
      setWeatherMeta(null)
      setDataRangeStart(null)
      setDataRangeEnd(null)
      setSeriesAsOfDate(null)
      setWindowDates(null)

      try {
        const data = await getLatestData(station.siteId, endDate)
        setDischargeSeries(ensure7(data.discharge, NaN))
        setPrcpSeries(ensure7(data.rainfall_mm, 0))
        const stageLoaded = (data.stage ?? []).map((v) => (typeof v === "number" ? v : NaN))
        setStageSeries(ensure7(stageLoaded, NaN))
        setTmaxSeries(ensure7(data.tmax_c, 0))
        setTminSeries(ensure7(data.tmin_c, 0))
        setAwndSeries(ensure7(data.awnd ?? [], 0))
        setSnowSeries(ensure7(data.snow ?? [], 0))
        setSnowDepthSeries(ensure7(data.snow_depth ?? [], 0))
        setWindowDates(data.dates.slice(0, 7))
        setDataRangeStart(data.data_start)
        setDataRangeEnd(data.data_end)
        setAutofillLabel(formatAutofillLabel(data.dates))
        setSeriesAsOfDate(data.latest_date)
        setWeatherMeta({
          rainfallAvailable: data.rainfall_available,
          weatherAvailable: data.weather_available,
        })
      } catch (e) {
        setLatestError(
          e instanceof Error ? e.message : "Could not load latest data for this station"
        )
        setDischargeSeries(nan7())
        setPrcpSeries(nan7())
        setStageSeries(nan7())
        setTmaxSeries(nan7())
        setTminSeries(nan7())
        setAwndSeries(nan7())
        setSnowSeries(nan7())
        setSnowDepthSeries(nan7())
      } finally {
        setLatestLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    loadLatestForStation(selectedStation)
  }, [selectedStation, loadLatestForStation])

  const handleStationChange = (station: Station) => {
    setSelectedStation(station)
    setResult(null)
    setStageResult(null)
    setError(null)
  }

  const handleWindowEndChange = (isoDate: string) => {
    loadLatestForStation(selectedStation, isoDate)
  }

  const handlePredict = async () => {
    const d = dischargeSeries.slice(0, 7)
    if (d.length < 7 || !d.every(Number.isFinite)) return

    setIsLoading(true)
    setError(null)

    try {
      const prediction = await getPrediction(selectedStation.siteId, d, {
        recentDischarge: d,
        recentPrcp: optionalFinite7(prcpSeries),
        recentTmax: optionalFinite7(tmaxSeries),
        recentTmin: optionalFinite7(tminSeries),
        recentAwnd: optionalFinite7(awndSeries),
        recentSnow: optionalFinite7(snowSeries),
        recentSnowDepth: optionalFinite7(snowDepthSeries),
        asOfDate: seriesAsOfDate ?? undefined,
      })
      setResult(prediction)
      const s = stageSeries.slice(0, 7)
      if (s.length === 7 && s.every(Number.isFinite)) {
        try {
          const st = await getStagePrediction(selectedStation.siteId, s, {
            recentDischarge: d,
            recentPrcp: optionalFinite7(prcpSeries),
            recentTmax: optionalFinite7(tmaxSeries),
            recentTmin: optionalFinite7(tminSeries),
            asOfDate: seriesAsOfDate ?? undefined,
          })
          setStageResult(st)
        } catch {
          setStageResult(null)
        }
      } else {
        setStageResult(null)
      }
      const latestHealth = await getApiHealth()
      if (latestHealth) setApiHealth(latestHealth)
    } catch (err) {
      const apiError = err as ApiError
      setError(apiError.message)
      if (apiError.isOffline) {
        setApiStatus(false)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <Header apiStatus={apiStatus} />

      <main className="w-full max-w-[min(100%,1600px)] mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-8">
          <PredictionCard
            selectedStation={selectedStation}
            onStationChange={handleStationChange}
            windowDates={windowDates}
            discharge={dischargeSeries}
            prcp={prcpSeries}
            tmax={tmaxSeries}
            tmin={tminSeries}
            awnd={awndSeries}
            snow={snowSeries}
            snow_depth={snowDepthSeries}
            onSeriesCellChange={handleSeriesCellChange}
            weatherHint={weatherHint}
            onPredict={handlePredict}
            isLoading={isLoading}
            error={error}
            latestLoading={latestLoading}
            latestError={latestError}
            autofillLabel={autofillLabel}
            dataRangeStart={dataRangeStart}
            dataRangeEnd={dataRangeEnd}
            windowEndDate={seriesAsOfDate}
            onWindowEndDateChange={handleWindowEndChange}
          />

          <ResultPanel
            result={result}
            stageResult={stageResult}
            dischargeValues={chartDischargeValues}
            station={selectedStation}
          />

          <AnalyticsDashboard
            result={result}
            stageResult={stageResult}
            dischargeValues={chartDischargeValues}
            apiHealth={apiHealth}
          />

          <DischargeChart values={chartDischargeValues} />
        </div>
      </main>
    </div>
  )
}
