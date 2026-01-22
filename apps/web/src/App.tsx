import { Shell } from "./components/layout/Shell";
import { NewResearchRunForm } from "./components/research/NewResearchRunForm";
import { RecentRunsPanel } from "./components/research/RecentRunsPanel";

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

      <main className="grid gap-6 lg:grid-cols-[2fr,1.2fr]">
        <section>
          <NewResearchRunForm />
        </section>
        <section>
          <RecentRunsPanel />
        </section>
      </main>
    </Shell>
  );
}

export default App;
