export function Header() {
  return (
    <header className="border-b border-slate-200/70 bg-white/70 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-sm" />
          <div>
            <div className="text-sm font-semibold text-slate-900">
              Flood Risk Predictor
            </div>
            <div className="text-xs text-slate-600">React + Vite + Tailwind</div>
          </div>
        </div>
        <div className="text-xs text-slate-600">
          API: <span className="font-mono">/predict</span>
        </div>
      </div>
    </header>
  )
}

