import { getApiBaseUrl, predictFloodRisk } from "/Users/yoannamaroun/Downloads/MachineLearning-CivilEngineering/frontend/vite-project/src/lib/api.js";
function parseRecentDischarge(input) {
  return input
    .split(/[,\s]+/g)
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => Number(x))
    .filter((n) => Number.isFinite(n));
}

export function PredictionCard() {
  const [siteId, setSiteId] = useState("01646500");
  const [asOfDate, setAsOfDate] = useState("");
  const [recentInput, setRecentInput] = useState(
    "100, 105, 110, 120, 130, 140, 150"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("Failed to fetch");
  const [result, setResult] = useState(null);

  const recentDischarge = useMemo(
    () => parseRecentDischarge(recentInput),
    [recentInput]
  );

  const apiBaseUrl = getApiBaseUrl();

  async function onPredict(e) {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!siteId.trim()) {
      setError("Please enter a site ID.");
      return;
    }

    if (recentDischarge.length < 7) {
      setError("Please provide at least 7 recent discharge values.");
      return;
    }

    setLoading(true);
    try {
      const payload = await predictFloodRisk({
        siteId: siteId.trim(),
        recentDischarge,
        asOfDate: asOfDate.trim() || undefined,
      });
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-8">
      <form onSubmit={onPredict} className="grid gap-6">
        <div className="grid gap-5">
          <label className="grid gap-2">
            <span className="text-2xl font-semibold tracking-tight text-slate-900">
              Site ID
            </span>
            <input
              value={siteId}
              onChange={(e) => setSiteId(e.target.value)}
              placeholder="01646500"
              className="h-16 rounded-2xl border border-slate-200 bg-white px-5 text-2xl font-medium text-slate-700 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
            />
          </label>

          <label className="grid gap-2">
            <span className="text-2xl font-semibold tracking-tight text-slate-900">
              Date (optional)
            </span>
            <div className="relative">
              <input
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
                placeholder="YYYY-MM-DD"
                className="h-16 w-full rounded-2xl border border-slate-200 bg-white px-5 pr-14 text-2xl font-medium text-slate-500 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
              />
              <div className="pointer-events-none absolute inset-y-0 right-5 flex items-center text-2xl text-slate-400">
                📅
              </div>
            </div>
          </label>

          <label className="grid gap-2">
            <span className="text-2xl font-semibold tracking-tight text-slate-900">
              Recent Discharge (7+ days)
            </span>
            <input
              value={recentInput}
              onChange={(e) => setRecentInput(e.target.value)}
              placeholder="100, 105, 110, 120, 130, 140, 150"
              className="h-16 rounded-2xl border border-slate-200 bg-white px-5 text-2xl font-medium text-slate-700 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
            />
            <p className="text-xl text-slate-500">
              Enter at least the past 7 daily discharge values, oldest → newest.
            </p>
          </label>
        </div>

        <div className="pt-1">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex min-w-[230px] items-center justify-center rounded-2xl bg-blue-600 px-8 py-4 text-3xl font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? "Predicting..." : "Predict"}
          </button>
        </div>

        <div className="grid gap-4">
          <p className="text-3xl font-medium text-slate-800">
            Parsed values: {recentDischarge.length}
          </p>

          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-3xl font-medium text-rose-700">
              {error}
            </div>
          ) : null}

          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-2xl text-slate-600">
            <span className="font-medium">Tip:</span> start your backend at{" "}
            <span className="font-semibold text-blue-600">localhost:8000</span>
          </div>
        </div>
      </form>

      <section className="pt-2">
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
          Next steps
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-8 text-2xl text-slate-600">
          <li>
            Point the UI to your backend with{" "}
            <span className="font-semibold text-blue-600">VITE_API_URL</span>.
          </li>
          <li>Replace the form with real “recent discharge” pulled from USGS.</li>
          <li>Add site metadata and thresholds for interpretability.</li>
        </ul>
      </section>

      {result ? (
        <section className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-2xl text-emerald-800">
          Prediction received successfully.
        </section>
      ) : null}

      <div className="hidden">{apiBaseUrl}</div>
    </div>
  );
}