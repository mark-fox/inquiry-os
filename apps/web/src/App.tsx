import { Shell } from "./components/layout/Shell";

function App() {
  return (
    <Shell>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          InquiryOS – AI Research Workspace
        </h1>
        <p className="mt-1 text-sm text-app-muted">
          A multi-agent research environment for planning, searching, reading,
          and synthesizing answers with traceable sources.
        </p>
      </header>

      <main>
        <section className="rounded-xl border border-app-border bg-app-surface p-6 shadow-soft">
          <h2 className="text-lg font-medium">New Research Run</h2>
          <p className="mt-2 text-sm text-app-muted">
            The UI will go here. Soon, you&apos;ll be able to ask complex
            questions and see full research plans, sources, and synthesized
            answers.
          </p>
        </section>
      </main>
    </Shell>
  );
}

export default App;
