export default function HomePage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <div className="border border-slate-200 bg-white rounded-lg p-8 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            RecoverAI
          </h1>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Phase 0 — Foundation
          </span>
        </div>

        <p className="text-slate-600 mb-6 text-base leading-relaxed">
          AI-powered Revenue Recovery platform. Detects revenue at risk, diagnoses
          underlying causes, recommends recovery interventions, and deterministically
          executes safety-governed actions.
        </p>

        <div className="border-t border-slate-100 pt-6">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-3">
            System Status
          </h2>
          <div className="bg-slate-50 border border-slate-200 rounded p-4 text-sm text-slate-700 space-y-1">
            <p>
              <span className="font-medium">Frontend:</span> Active (Next.js & Tailwind CSS)
            </p>
            <p>
              <span className="font-medium">Backend Service:</span> FastAPI (Endpoint: <code className="bg-slate-200 px-1 py-0.5 rounded text-xs">/health</code>)
            </p>
            <p>
              <span className="font-medium">Status:</span> Foundation established
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
