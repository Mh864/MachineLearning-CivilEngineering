import { useMemo, useState } from "react";

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
  const predictionValue =
    typeof result?.prediction !== "undefined"
      ? Number(result.prediction)
      : values.length >= 2 && values[values.length - 1] > values[0]
      ? 1
      : 0;

  const confidence =
    typeof result?.confidence === "number"
      ? Math.round(result.confidence * 100)
      : predictionValue === 1
      ? 78
      : 32;

  if (predictionValue === 1) {
    return {
      label: "Medium Risk",
      badgeClass:
        "bg-amber-100 text-amber-700 border border-amber-200",
      dotClass: "bg-amber-500",
      confidence,
      description:
        "Recent discharge trend is increasing, which may indicate elevated flood risk.",
    };
  }

  return {
    label: "Low Risk",
    badgeClass:
      "bg-emerald-100 text-emerald-700 border border-emerald-200",
    dotClass: "bg-emerald-500",
    confidence,
    description:
      "Discharge trend looks stable for now, suggesting lower flood risk.",
  };
}

function TinyChart({ values = [] }) {
  const width = 360;
  const height = 150;
  const padding = 18;

  if (!values.length) {
    return (
      <div className="flex h-[150px] items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">
        No data yet
      </div>
    );
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values.map((value, index) => {
    const x =
      padding +
      (index * (width - padding * 2)) / Math.max(values.length - 1, 1);
    const y =
      height - padding - ((value - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const areaPoints = [
    `${padding},${height - padding}`,
    ...points,
    `${width - padding},${height - padding}`,
  ].join(" ");

  const lastX =
    padding +
    ((values.length - 1) * (width - padding * 2)) /
      Math.max(values.length - 1, 1);

  const lastY =
    height -
    padding -
    ((values[values.length - 1] - min) / range) * (height - padding * 2);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-[150px] w-full"
        aria-label="Recent discharge chart"
      >
        <defs>
          <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgb(59 130 246)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="rgb(59 130 246)" stopOpacity="0.03" />
          </linearGradient>
        </defs>

        {[0, 1, 2].map((line) => {
          const y = padding + (line * (height - padding * 2)) / 2;
          return (
            <line
              key={line}
              x1={padding}
              y1={y}
              x2={width - padding}
              y2={y}
              stroke="#e2e8f0"
              strokeDasharray="4 4"
            />
          );
        })}

        <polygon points={areaPoints} fill="url(#areaFill)" />
        <polyline
          fill="none"
          stroke="#3b82f6"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points.join(" ")}
        />
        <circle cx={lastX} cy={lastY} r="5" fill="#3b82f6" />
        <circle cx={lastX} cy={lastY} r="9" fill="#3b82f6" opacity="0.12" />
      </svg>

      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span>Oldest</span>
        <span>Newest</span>
      </div>
    </div>
  );
}

function ResultPanel({ values, result }) {
  const risk = getRiskInfo(result, values);

  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${risk.dotClass}`} />
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${risk.badgeClass}`}
            >
              {risk.label}
            </span>
          </div>

          <div className="text-right">
            <div className="text-2xl font-semibold text-slate-900">
              {risk.confidence}%
            </div>
            <div className="text-xs text-slate-500">Confidence</div>
          </div>
        </div>

        <TinyChart values={values} />

        <p className="mt-4 text-sm leading-6 text-slate-600">
          {risk.description}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Parsed Values</div>
          <div className="mt-1 text-lg font-semibold text-slate-900">
            {values.length}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Backend</div>
          <div className="mt-1 text-sm font-medium text-emerald-600">
            Ready
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Site ID</div>
          <div className="mt-1 truncate text-sm font-medium text-slate-900">
            {result?.site_id || "01646500"}
          </div>
        </div>
      </div>

      {result ? (
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-3 text-xs text-slate-700">
          <div className="mb-1 font-semibold text-slate-800">API Response</div>
          <pre className="overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

export default function App() {
  const [siteId, setSiteId] = useState("01646500");
  const [date, setDate] = useState("");
  const [discharge, setDischarge] = useState(
    "100, 105, 110, 120, 130, 140, 150"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("Failed to fetch");
  const [result, setResult] = useState(null);

  const parsedValues = useMemo(
    () => parseRecentDischarge(discharge),
    [discharge]
  );

  async function handlePredict(e) {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!siteId.trim()) {
      setError("Please enter a site ID.");
      return;
    }

    if (parsedValues.length < 7) {
      setError("Please enter at least 7 discharge values.");
      return;
    }

    setLoading(true);

    try {
      const baseUrl = getApiBaseUrl().replace(/\/$/, "");
      const params = new URLSearchParams();
      params.set("site_id", siteId.trim());
      params.set("recent_discharge", parsedValues.join(","));
      if (date.trim()) params.set("as_of_date", date.trim());

      const res = await fetch(`${baseUrl}/predict?${params.toString()}`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text.slice(0, 200)}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-50 via-slate-50 to-white text-slate-900">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-sm">
            </div>

            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-900">
                Flood Risk Predictor
              </h1>
              <p className="text-xs text-slate-500">
                Simple flood-risk dashboard
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-3 text-sm text-slate-500 md:flex">
            <span>React + Vite + Tailwind</span>
            <span className="text-slate-300">•</span>
            <span>
              API: <span className="font-semibold text-slate-800">/predict</span>
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <section className="mb-6">
        
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl">
            Make a prediction
          </h2>
          <p className="mt-2 max-w-2xl text-base text-slate-600">
            Enter a site ID and recent discharge data to estimate current flood
            risk in a cleaner, more visual dashboard.
          </p>
        </section>

        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <form onSubmit={handlePredict} className="grid gap-4">
              <div className="grid gap-4">
                <label className="grid gap-2">
                  <span className="text-sm font-medium text-slate-700">
                    Site ID
                  </span>
                  <input
                    value={siteId}
                    onChange={(e) => setSiteId(e.target.value)}
                    placeholder="01646500"
                    className="h-10 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
                  />
                </label>

                <label className="grid gap-2">
                  <span className="text-sm font-medium text-slate-700">
                    Date (optional)
                  </span>
                  <div className="relative">
                    <input
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                      placeholder="YYYY-MM-DD"
                      className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 pr-10 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
                    />
                    <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-slate-400">
                      📅
                    </div>
                  </div>
                </label>

                <label className="grid gap-2">
                  <span className="text-sm font-medium text-slate-700">
                    Recent Discharge (7+ days)
                  </span>
                  <input
                    value={discharge}
                    onChange={(e) => setDischarge(e.target.value)}
                    placeholder="100, 105, 110, 120, 130, 140, 150"
                    className="h-10 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
                  />
                  <p className="text-sm text-slate-500">
                    Enter at least the past 7 daily discharge values, oldest →
                    newest.
                  </p>
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 focus:ring-2 focus:ring-blue-200 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? "Predicting..." : "Predict"}
                </button>

                <div className="inline-flex items-center gap-2 text-sm text-slate-600">
                  Parsed values:
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {parsedValues.length}
                  </span>
                </div>
              </div>

              {error ? (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
                  {error}
                </div>
              ) : null}

              <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-2 text-sm text-blue-700">
                <span className="font-medium">Tip:</span> start your backend at{" "}
                <span className="font-semibold">localhost:8000</span>
              </div>

              <section className="mt-2 rounded-xl bg-slate-50 p-4">
                <h3 className="text-sm font-semibold text-slate-900">
                  Next steps
                </h3>
                <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-600">
                  <li>
                    Point the UI to your backend with{" "}
                    <span className="font-semibold text-blue-600">
                      VITE_API_URL
                    </span>
                    .
                  </li>
                  <li>
                    Replace the form with real recent discharge pulled from USGS.
                  </li>
                  <li>Add site metadata and thresholds for interpretability.</li>
                </ul>
              </section>
            </form>
          </div>

          <ResultPanel values={parsedValues} result={result} />
        </div>
      </main>
    </div>
  );
}