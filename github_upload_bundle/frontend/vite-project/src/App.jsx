import { useMemo, useState } from "react";

/* ─── helpers ─────────────────────────────────────────────────────────────── */

function parseRecentDischarge(input) {
  return input
    .split(/[,\s]+/g)
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => Number(x))
    .filter((n) => Number.isFinite(n));
}

function getApiBaseUrl() {
  return import.meta.env.VITE_API_URL || "http://localhost:8000";
}

function getRiskInfo(result, values) {
  const prediction =
    typeof result?.prediction !== "undefined"
      ? Number(result.prediction)
      : values.length >= 2 && values[values.length - 1] > values[0]
      ? 1
      : 0;

  const confidence =
    typeof result?.confidence === "number"
      ? Math.round(result.confidence * 100)
      : prediction === 1
      ? 72
      : 35;

  if (prediction === 1) {
    return {
      label: "Elevated Risk",
      emoji: "⚠️",
      badgeBg: "bg-amber-100",
      badgeText: "text-amber-800",
      badgeBorder: "border-amber-300",
      dotBg: "bg-amber-500",
      barBg: "bg-amber-500",
      cardBg: "bg-amber-50",
      cardBorder: "border-amber-200",
      description:
        "Discharge trend is increasing. Elevated flood risk has been detected for the next day.",
      confidence,
    };
  }

  return {
    label: "Low Risk",
    emoji: "✅",
    badgeBg: "bg-emerald-100",
    badgeText: "text-emerald-800",
    badgeBorder: "border-emerald-300",
    dotBg: "bg-emerald-500",
    barBg: "bg-emerald-500",
    cardBg: "bg-emerald-50",
    cardBorder: "border-emerald-200",
    description:
      "Discharge trend appears stable. Lower flood risk is expected for the next day.",
    confidence,
  };
}

/* ─── DischargeChart ───────────────────────────────────────────────────────── */

function DischargeChart({ values = [] }) {
  const W = 520;
  const H = 190;
  const pad = { top: 18, right: 18, bottom: 32, left: 48 };

  if (!values.length) {
    return (
      <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-200 bg-slate-50">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
          <path d="M3 17s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
          <line x1="3" y1="21" x2="21" y2="21" />
        </svg>
        <p className="text-sm text-slate-400">Enter discharge values to preview the chart</p>
      </div>
    );
  }

  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const pts = values.map((v, i) => [
    pad.left + (i * iW) / Math.max(values.length - 1, 1),
    pad.top + iH - ((v - min) / range) * iH,
  ]);

  const line = pts.map(([x, y]) => `${x},${y}`).join(" ");
  const area = [
    `${pad.left},${pad.top + iH}`,
    ...pts.map(([x, y]) => `${x},${y}`),
    `${pad.left + iW},${pad.top + iH}`,
  ].join(" ");

  const [lx, ly] = pts[pts.length - 1];
  const rising = values[values.length - 1] > values[0];
  const color = rising ? "#f59e0b" : "#10b981";
  const gradId = rising ? "gradAmber" : "gradGreen";

  const yTicks = [0, 0.5, 1].map((t) => ({
    y: pad.top + iH - t * iH,
    v: (min + t * range).toFixed(0),
  }));

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Discharge Trend
        </span>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            rising
              ? "bg-amber-100 text-amber-700"
              : "bg-emerald-100 text-emerald-700"
          }`}
        >
          {rising ? "↑ Rising" : "↓ Stable / Falling"}
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="h-48 w-full">
        <defs>
          <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.22" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {yTicks.map(({ y, v }) => (
          <g key={v}>
            <line
              x1={pad.left} y1={y} x2={pad.left + iW} y2={y}
              stroke="#e2e8f0" strokeDasharray="4 3" strokeWidth="1"
            />
            <text x={pad.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#94a3b8">
              {v}
            </text>
          </g>
        ))}

        {[0, Math.floor((values.length - 1) / 2), values.length - 1].map((i) => (
          <text
            key={i}
            x={pts[i][0]}
            y={H - 6}
            textAnchor="middle"
            fontSize="10"
            fill="#94a3b8"
          >
            Day {i + 1}
          </text>
        ))}

        <polygon points={area} fill={`url(#${gradId})`} />
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={line}
        />

        {pts.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="3" fill={color} opacity="0.55" />
        ))}

        <circle cx={lx} cy={ly} r="5" fill={color} />
        <circle cx={lx} cy={ly} r="11" fill={color} opacity="0.12" />
      </svg>

      <div className="mt-1 flex justify-between text-xs text-slate-400">
        <span>Oldest</span>
        <span>{values.length} data points</span>
        <span>Newest</span>
      </div>
    </div>
  );
}

/* ─── StatsRow ─────────────────────────────────────────────────────────────── */

function StatsRow({ values }) {
  if (!values.length) return null;
  const min = Math.min(...values).toFixed(1);
  const max = Math.max(...values).toFixed(1);
  const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
  const last = values[values.length - 1].toFixed(1);

  const items = [
    { label: "Min", value: min },
    { label: "Avg", value: avg },
    { label: "Max", value: max },
    { label: "Latest", value: last },
  ];

  return (
    <div className="grid grid-cols-4 gap-2">
      {items.map(({ label, value }) => (
        <div
          key={label}
          className="rounded-xl border border-slate-200 bg-white p-3 text-center shadow-sm"
        >
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            {label}
          </div>
          <div className="mt-1 text-base font-bold text-slate-800">{value}</div>
          <div className="text-[10px] text-slate-400">cfs</div>
        </div>
      ))}
    </div>
  );
}

/* ─── ResultPanel ──────────────────────────────────────────────────────────── */

function ResultPanel({ values, result, loading }) {
  const risk = getRiskInfo(result, values);

  return (
    <div className="grid gap-4 content-start">
      {/* Risk card */}
      <div
        className={`rounded-2xl border p-5 shadow-sm transition-all duration-500 animate-slide-up ${
          loading
            ? "border-slate-200 bg-slate-50"
            : result
            ? `${risk.cardBg} ${risk.cardBorder}`
            : "border-slate-200 bg-white"
        }`}
      >
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-3 py-10">
            <div className="h-8 w-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            <p className="text-sm font-medium text-slate-500">Analyzing discharge data…</p>
          </div>
        ) : result ? (
          <div className="animate-slide-up">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <span
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-semibold ${risk.badgeBg} ${risk.badgeText} ${risk.badgeBorder}`}
                >
                  <span className={`h-2 w-2 rounded-full ${risk.dotBg}`} />
                  {risk.label}
                </span>
                <p className="mt-3 text-sm leading-relaxed text-slate-700">
                  {risk.description}
                </p>
              </div>
              <span className="text-3xl">{risk.emoji}</span>
            </div>

            <div className="mt-2">
              <div className="mb-1.5 flex justify-between text-xs font-medium text-slate-500">
                <span>Model confidence</span>
                <span className="text-slate-700">{risk.confidence}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${risk.barBg}`}
                  style={{ width: `${risk.confidence}%` }}
                />
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl bg-white/70 border border-slate-200 p-3">
                <p className="text-slate-400 font-medium">Site ID</p>
                <p className="mt-0.5 font-semibold text-slate-800">{result.site_id || "—"}</p>
              </div>
              <div className="rounded-xl bg-white/70 border border-slate-200 p-3">
                <p className="text-slate-400 font-medium">Raw Prediction</p>
                <p className="mt-0.5 font-semibold text-slate-800">{result.prediction ?? "—"}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 border border-blue-100 text-3xl">
              🌊
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700">No prediction yet</p>
              <p className="mt-1 text-xs text-slate-400">
                Fill in the form on the left and click{" "}
                <span className="font-medium text-blue-600">Run Prediction</span>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Chart */}
      <DischargeChart values={values} />

      {/* Stats */}
      <StatsRow values={values} />

      {/* API response */}
      {result && (
        <div className="animate-slide-up rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Raw API Response
          </p>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ─── Site list ────────────────────────────────────────────────────────────── */

const SITES = [
  { id: "01646500", name: "Potomac River at Point of Rocks, MD" },
  { id: "02087500", name: "Neuse River near Clayton, NC" },
  { id: "03015500", name: "Allegheny River at Eldred, PA" },
  { id: "05054000", name: "Red River of the North at Fargo, ND" },
  { id: "06710247", name: "Cherry Creek at Denver, CO" },
  { id: "08066500", name: "Trinity River at Romayor, TX" },
  { id: "09380000", name: "Colorado River near Lees Ferry, AZ" },
  { id: "11425500", name: "Sacramento River at Verona, CA" },
  { id: "12301933", name: "Clark Fork above Missoula, MT" },
  { id: "14211720", name: "Willamette River at Portland, OR" },
];

/* ─── App ──────────────────────────────────────────────────────────────────── */

export default function App() {
  const [siteId, setSiteId] = useState(SITES[0].id);
  const [date, setDate] = useState("");
  const [discharge, setDischarge] = useState(
    "100, 105, 110, 120, 130, 140, 150"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const parsedValues = useMemo(
    () => parseRecentDischarge(discharge),
    [discharge]
  );

  const canSubmit = parsedValues.length >= 7 && siteId.trim().length > 0;

  async function handlePredict(e) {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!siteId.trim()) {
      setError("Please enter a USGS site ID.");
      return;
    }
    if (parsedValues.length < 7) {
      setError(
        `At least 7 discharge values required — you've entered ${parsedValues.length}.`
      );
      return;
    }

    setLoading(true);
    try {
      const base = getApiBaseUrl().replace(/\/$/, "");
      const params = new URLSearchParams({
        site_id: siteId.trim(),
        recent_discharge: parsedValues.join(","),
      });
      if (date.trim()) params.set("as_of_date", date.trim());

      const res = await fetch(`${base}/predict?${params}`, {
        headers: { Accept: "application/json" },
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`API error ${res.status}: ${txt.slice(0, 200)}`);
      }

      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect to API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100">
      {/* ── Header ── */}
      <header className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950">
        {/* decorative circles */}
        <div className="pointer-events-none absolute -top-20 -right-20 h-72 w-72 rounded-full bg-blue-500/10" />
        <div className="pointer-events-none absolute -bottom-10 -left-10 h-48 w-48 rounded-full bg-indigo-500/10" />

        <div className="relative mx-auto max-w-6xl px-6 py-10">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-blue-400/30 bg-blue-500/20 text-3xl backdrop-blur-sm">
                🌊
              </div>
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight text-white md:text-3xl">
                  Flood Risk Predictor
                </h1>
                <p className="mt-1 text-sm text-blue-300">
                  ML-powered next-day discharge risk analysis · USGS + NOAA
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              {[
                { icon: "🤖", label: "Model", value: "LogReg + LightGBM" },
                { icon: "📅", label: "Horizon", value: "Next-day forecast" },
                { icon: "📍", label: "Source", value: "USGS gauges" },
              ].map(({ icon, label, value }) => (
                <div
                  key={label}
                  className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 backdrop-blur-sm"
                >
                  <span>{icon}</span>
                  <div>
                    <p className="text-[10px] font-medium uppercase tracking-wider text-blue-300">
                      {label}
                    </p>
                    <p className="text-xs font-semibold text-white">{value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* wave bottom edge */}
        <svg
          viewBox="0 0 1440 40"
          className="block w-full"
          preserveAspectRatio="none"
          style={{ height: 40, marginBottom: -1 }}
        >
          <path
            d="M0,20 C360,40 1080,0 1440,20 L1440,40 L0,40 Z"
            fill="#f1f5f9"
          />
        </svg>
      </header>

      {/* ── Main ── */}
      <main className="mx-auto max-w-6xl px-6 pb-16">
        <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          {/* ── Form card ── */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 bg-slate-50 px-6 py-4">
              <h2 className="text-base font-semibold text-slate-900">
                Prediction Input
              </h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Provide your gauge ID and recent discharge readings
              </p>
            </div>

            <form onSubmit={handlePredict} className="grid gap-5 p-6">
              {/* Site ID */}
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">
                  Gauge Site
                </label>
                <select
                  value={siteId}
                  onChange={(e) => setSiteId(e.target.value)}
                  className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100 cursor-pointer"
                >
                  {SITES.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">
                  As-of Date{" "}
                  <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <input
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  placeholder="YYYY-MM-DD"
                  className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  Defaults to today (UTC) — used for the month feature
                </p>
              </div>

              {/* Discharge */}
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="text-sm font-medium text-slate-700">
                    Recent Discharge Values
                  </label>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold transition ${
                      parsedValues.length >= 7
                        ? "bg-emerald-100 text-emerald-700"
                        : parsedValues.length > 0
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {parsedValues.length >= 7 ? "✓" : parsedValues.length}{" "}
                    {parsedValues.length >= 7 ? "Ready" : "/ 7 min"}
                  </span>
                </div>

                <textarea
                  value={discharge}
                  onChange={(e) => setDischarge(e.target.value)}
                  placeholder="100, 105, 110, 120, 130, 140, 150"
                  rows={3}
                  className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  Comma or space-separated · oldest → newest · minimum 7 values
                </p>
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 animate-slide-up">
                  <span className="mt-0.5 text-red-500">⚠</span>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading || !canSubmit}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 text-sm font-semibold text-white shadow-sm transition active:scale-[0.98] hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    Analyzing…
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <circle cx="11" cy="11" r="8" />
                      <path d="m21 21-4.35-4.35" />
                    </svg>
                    Run Prediction
                  </>
                )}
              </button>

            </form>
          </div>

          {/* ── Result panel ── */}
          <ResultPanel values={parsedValues} result={result} loading={loading} />
        </div>
      </main>
    </div>
  );
}
