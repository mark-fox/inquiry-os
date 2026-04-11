import { useState } from "react";
import { Shell } from "./components/layout/Shell";
import { NewResearchRunForm } from "./components/research/NewResearchRunForm";
import { RecentRunsPanel } from "./components/research/RecentRunsPanel";

function App() {
  const [autoRunId, setAutoRunId] = useState<string | null>(null);

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

      <main className="grid gap-6 lg:grid-cols-[2fr,1.2fr]">
        <section>
          <NewResearchRunForm onRunCreated={setAutoRunId} />
        </section>
        <section>
          <RecentRunsPanel autoRunId={autoRunId} />
        </section>
      </main>
    </Shell>
  );
}

export default App;