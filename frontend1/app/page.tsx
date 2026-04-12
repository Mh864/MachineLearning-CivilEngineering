"use client"

import { useState, useEffect, useCallback } from "react"
import { format, parseISO } from "date-fns"
import { Header } from "@/components/flood/Header"
import { PredictionCard } from "@/components/flood/PredictionCard"
import { ResultPanel } from "@/components/flood/ResultPanel"
import { DischargeChart } from "@/components/flood/DischargeChart"
import { STATIONS, type Station } from "@/lib/constants"
import {
  checkApiStatus,
  getLatestData,
  getPrediction,
  parseDischargeInput,
  type PredictionResponse,
  type ApiError,
} from "@/lib/api"

function formatAutofillLabel(dates: string[]): string {
  if (dates.length === 0) return ""
  const first = parseISO(dates[0])
  const last = parseISO(dates[dates.length - 1])
  return `Auto-filled from USGS data — ${format(first, "MMM d")} to ${format(last, "MMM d, yyyy")}`
}

export default function Dashboard() {
  const [apiStatus, setApiStatus] = useState<boolean | null>(null)
  const [selectedStation, setSelectedStation] = useState<Station>(STATIONS[0])
  const [dischargeInput, setDischargeInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PredictionResponse | null>(null)
  const [latestLoading, setLatestLoading] = useState(false)
  const [latestError, setLatestError] = useState<string | null>(null)
  const [autofillLabel, setAutofillLabel] = useState<string | null>(null)
  const [rainfallMm, setRainfallMm] = useState<number[] | null>(null)
  const [tmaxSeries, setTmaxSeries] = useState<number[] | null>(null)
  const [tminSeries, setTminSeries] = useState<number[] | null>(null)
  const [dataRangeStart, setDataRangeStart] = useState<string | null>(null)
  const [dataRangeEnd, setDataRangeEnd] = useState<string | null>(null)
  /** Last day of the loaded USGS window — passed as as_of_date so month matches training. */
  const [seriesAsOfDate, setSeriesAsOfDate] = useState<string | null>(null)

  const parsedValues = parseDischargeInput(dischargeInput)

  useEffect(() => {
    checkApiStatus().then(setApiStatus)
  }, [])

  const loadLatestForStation = useCallback(
    async (station: Station, endDate?: string) => {
      setLatestLoading(true)
      setLatestError(null)
      setAutofillLabel(null)
      setRainfallMm(null)
      setTmaxSeries(null)
      setTminSeries(null)
      setDataRangeStart(null)
      setDataRangeEnd(null)
      setSeriesAsOfDate(null)

      try {
        const data = await getLatestData(station.siteId, endDate)
        setDischargeInput(data.discharge.map(String).join(", "))
        setRainfallMm(data.rainfall_mm)
        setTmaxSeries(data.tmax_c)
        setTminSeries(data.tmin_c)
        setDataRangeStart(data.data_start)
        setDataRangeEnd(data.data_end)
        setAutofillLabel(formatAutofillLabel(data.dates))
        setSeriesAsOfDate(data.latest_date)
      } catch (e) {
        setLatestError(
          e instanceof Error ? e.message : "Could not load latest data for this station"
        )
        setDischargeInput("")
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
    setError(null)
  }

  const handleWindowEndChange = (isoDate: string) => {
    loadLatestForStation(selectedStation, isoDate)
  }

  const handlePredict = async () => {
    if (parsedValues.length < 7) return

    setIsLoading(true)
    setError(null)

    try {
      const prediction = await getPrediction(selectedStation.siteId, parsedValues, {
        recentPrcp:
          rainfallMm && rainfallMm.length >= 7 ? rainfallMm : undefined,
        recentTmax:
          tmaxSeries && tmaxSeries.length >= 7 ? tmaxSeries : undefined,
        recentTmin:
          tminSeries && tminSeries.length >= 7 ? tminSeries : undefined,
        asOfDate: seriesAsOfDate ?? undefined,
      })
      setResult(prediction)
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

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-2">
          <PredictionCard
            selectedStation={selectedStation}
            onStationChange={handleStationChange}
            dischargeInput={dischargeInput}
            onDischargeChange={setDischargeInput}
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
            dischargeValues={parsedValues}
            station={selectedStation}
          />
        </div>

        <div className="mt-6">
          <DischargeChart values={parsedValues} />
        </div>
      </main>
    </div>
  )
}
