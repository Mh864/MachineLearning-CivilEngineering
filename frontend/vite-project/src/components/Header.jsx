export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 md:px-8 lg:px-10">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-sm">
            <span className="text-lg"></span>
          </div>

          <div>
            <div className="text-2xl font-semibold tracking-tight text-slate-900">
              Flood Risk Predictor
            </div>
          </div>
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <span className="text-sm font-medium text-slate-500">
            React + Vite + Tailwind
          </span>
          <span className="text-slate-300">•</span>
          <span className="text-sm font-medium text-slate-600">
            API: <span className="font-semibold text-slate-800">/predict</span>
          </span>
        </div>
      </div>
    </header>
  );
}