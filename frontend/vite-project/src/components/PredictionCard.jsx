import { useMemo, useState } from 'react'
import { getApiBaseUrl, predictFloodRisk } from '../lib/api'

function parseRecentDischarge(input) {
  const parts = input
    .split(/[,\s]+/g)
    .map((x) => x.trim())
    .filter(Boolean)

  const nums = parts
    .map((x) => Number(x))
    .filter((n) => Number.isFinite(n))

  return nums
}

function ResultBadge({ prediction }) {
  const isRisk = prediction === 1
  return (
    <div
      className={[
        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium',
        isRisk ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800',
      ].join(' ')}
    >
      <span className={['h-2 w-2 rounded-full', isRisk ? 'bg-rose-600' : 'bg-emerald-600'].join(' ')} />
      {isRisk ? 'Risk likely (1)' : 'No risk likely (0)'}
    </div>
  )
}

export function PredictionCard() {
  const [siteId, setSiteId] = useState('01646500')
  const [asOfDate, setAsOfDate] = useState('')
  const [recentInput, setRecentInput] = useState('100, 105, 110, 120, 130, 140, 150')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const recentDischarge = useMemo(() => parseRecentDischarge(recentInput), [recentInput])
  const apiBaseUrl = getApiBaseUrl()

  async function onPredict(e) {
    e.preventDefault()
    setError('')
    setResult(null)

    if (!siteId.trim()) {
      setError('Please enter a site_id.')
      return
    }
    if (recentDischarge.length < 7) {
      setError('Please provide at least 7 recent discharge values (oldest → newest).')
      return
    }

    setLoading(true)
    try {
      const payload = await predictFloodRisk({
        siteId: siteId.trim(),
        recentDischarge,
        asOfDate: asOfDate.trim() || undefined,
      })
      setResult(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-6 py-5">
        <h1 className="text-lg font-semibold text-slate-900">Make a prediction</h1>
        <p className="mt-1 text-sm text-slate-600">
          Calls your FastAPI endpoint at{' '}
          <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-800">
            {apiBaseUrl}
          </span>
          . Set <span className="font-mono">VITE_API_URL</span> to change it.
        </p>
      </div>

      <form onSubmit={onPredict} className="grid gap-5 p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-slate-800">site_id</span>
            <input
              value={siteId}
              onChange={(e) => setSiteId(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/30"
              placeholder="01646500"
            />
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-slate-800">as_of_date (optional)</span>
            <input
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/30"
              placeholder="YYYY-MM-DD"
            />
          </label>
        </div>

        <label className="grid gap-1.5">
          <span className="text-sm font-medium text-slate-800">
            recent_discharge (need ≥ 7, oldest → newest)
          </span>
          <textarea
            value={recentInput}
            onChange={(e) => setRecentInput(e.target.value)}
            rows={3}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/30"
            placeholder="e.g. 100, 105, 110, 120, 130, 140, 150"
          />
          <div className="text-xs text-slate-500">
            Parsed values: <span className="font-mono">{recentDischarge.length}</span>
          </div>
        </label>

        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}
          </div>
        ) : null}

        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? 'Predicting…' : 'Predict'}
          </button>

          {result && typeof result.prediction !== 'undefined' ? (
            <ResultBadge prediction={Number(result.prediction)} />
          ) : (
            <div className="text-xs text-slate-500">
              Tip: start your backend at <span className="font-mono">localhost:8000</span>
            </div>
          )}
        </div>
      </form>
    </section>
  )
}

