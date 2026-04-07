import { Header } from './components/Header'
import { PredictionCard } from './components/PredictionCard'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <Header />
      <main className="mx-auto grid max-w-5xl gap-6 px-4 py-10">
        <PredictionCard />
        <section className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
          <div className="font-medium text-slate-900">Next steps</div>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>
              Point the UI to your backend with{' '}
              <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-800">
                VITE_API_URL
              </span>
              .
            </li>
            <li>Replace the form with real “recent discharge” pulled from USGS.</li>
            <li>Add site metadata and thresholds for interpretability.</li>
          </ul>
        </section>
      </main>
    </div>
  )
}

export default App
