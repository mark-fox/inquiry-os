import { useEffect, useState } from "react";
import type { ResearchRunRead, ResearchRunDetail } from "../../api/research";
import {
    listResearchRuns,
    getResearchRunDetail,
    runDummySearch,
    runDummySynthesis,
} from "../../api/research";

function formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}

export function RecentRunsPanel() {
    const [runs, setRuns] = useState<ResearchRunRead[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDetail, setSelectedDetail] = useState<ResearchRunDetail | null>(
        null,
    );
    const [isDetailLoading, setIsDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState<string | null>(null);
    const [isSearchRunning, setIsSearchRunning] = useState(false);
    const [isSynthesisRunning, setIsSynthesisRunning] = useState(false);

    useEffect(() => {
        let cancelled = false;

        async function loadRuns() {
            setIsLoading(true);
            setError(null);

            try {
                const data = await listResearchRuns(10, 0);
                if (!cancelled) {
                    setRuns(data);
                }
            } catch (err) {
                if (!cancelled) {
                    const message =
                        err instanceof Error ? err.message : "Failed to load runs.";
                    setError(message);
                }
            } finally {
                if (!cancelled) {
                    setIsLoading(false);
                }
            }
        }

        loadRuns();

        return () => {
            cancelled = true;
        };
    }, []);

    async function handleSelectRun(runId: string) {
        setIsDetailLoading(true);
        setDetailError(null);

        try {
            const detail = await getResearchRunDetail(runId);
            setSelectedDetail(detail);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to load run details.";
            setDetailError(message);
        } finally {
            setIsDetailLoading(false);
        }
    }


    async function handleRunDummySearch() {
        if (!selectedDetail) return;

        setIsSearchRunning(true);
        setDetailError(null);

        try {
            const updated = await runDummySearch(selectedDetail.id);
            setSelectedDetail(updated);

            // Optional: refresh the list so status / timestamps stay in sync
            try {
                const refreshedRuns = await listResearchRuns(10, 0);
                setRuns(refreshedRuns);
            } catch {
                // if this fails, it's non-fatal for now
            }
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to run dummy search.";
            setDetailError(message);
        } finally {
            setIsSearchRunning(false);
        }
    }


    function getSynthAnswer(detail: ResearchRunDetail | null): string | null {
        if (!detail) return null;

        const step = detail.steps.find(
            (s) => s.step_type === "synthesizer",
        );
        if (!step || !step.output) return null;

        const out = step.output as Record<string, unknown>;
        const value = out["answer"];

        return typeof value === "string" ? value : null;
    }


    async function handleRunDummySynthesis() {
        if (!selectedDetail) return;

        setIsSynthesisRunning(true);
        setDetailError(null);

        try {
            const updated = await runDummySynthesis(selectedDetail.id);
            setSelectedDetail(updated);

            // Optional: refresh the run list so you see updated status if it changes
            try {
                const refreshedRuns = await listResearchRuns(10, 0);
                setRuns(refreshedRuns);
            } catch {
                // non-fatal
            }
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to run dummy synthesis.";
            setDetailError(message);
        } finally {
            setIsSynthesisRunning(false);
        }
    }


    return (
        <aside className="rounded-xl border border-app-border bg-app-surface p-4 shadow-soft">
            <h2 className="text-sm font-semibold">Recent runs</h2>
            <p className="mt-1 text-xs text-app-muted">
                Latest research runs in this workspace.
            </p>

            {isLoading && (
                <p className="mt-3 text-sm text-app-muted">Loading…</p>
            )}

            {error && (
                <p className="mt-3 text-sm text-red-400">{error}</p>
            )}

            {!isLoading && !error && runs.length === 0 && (
                <p className="mt-3 text-sm text-app-muted">
                    No runs yet. Create a new research run to get started.
                </p>
            )}

            {!isLoading && !error && runs.length > 0 && (
                <ul className="mt-3 space-y-2">
                    {runs.map((run) => {
                        const isSelected = selectedDetail?.id === run.id;

                        return (
                            <li
                                key={run.id}
                                onClick={() => handleSelectRun(run.id)}
                                className={`rounded-lg border bg-black/30 p-3 text-left transition ${isSelected
                                    ? "border-app-accent bg-black/40"
                                    : "border-app-border hover:border-app-accent/60 hover:bg-black/40 cursor-pointer"
                                    }`}
                            >
                                <p className="text-xs font-semibold text-app-text">
                                    {run.title || "Untitled run"}
                                </p>
                                <p className="mt-1 line-clamp-2 text-xs text-app-muted">
                                    {run.query}
                                </p>
                                <div className="mt-2 flex items-center justify-between">
                                    <span className="rounded-full bg-app-bg px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-app-accent">
                                        {run.status}
                                    </span>
                                    <span className="text-[10px] text-app-muted">
                                        {formatDate(run.created_at)}
                                    </span>
                                </div>
                            </li>
                        );
                    })}
                </ul>
            )}

            {selectedDetail && !isDetailLoading && !detailError && (
                <div className="mt-4 rounded-lg border border-app-border bg-app-bg/60 p-3">
                    <h3 className="text-xs font-semibold">Selected run</h3>
                    <p className="mt-1 text-[11px] text-app-muted">
                        {selectedDetail.title || "Untitled run"}
                    </p>
                    <p className="mt-1 text-[11px] text-app-muted">
                        {selectedDetail.query}
                    </p>

                    <p className="mt-2 text-[10px] text-app-muted">
                        Status:{" "}
                        <span className="font-semibold text-app-accent">
                            {selectedDetail.status}
                        </span>
                    </p>

                    <p className="mt-1 text-[10px] text-app-muted">
                        Model:{" "}
                        <span className="font-mono">{selectedDetail.model_provider}</span>
                    </p>

                    <button
                        type="button"
                        onClick={handleRunDummySearch}
                        disabled={isSearchRunning}
                        className="mt-2 inline-flex items-center rounded-md bg-app-accent px-2.5 py-1 text-[11px] font-medium text-app-bg transition hover:bg-app-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSearchRunning ? "Running dummy search…" : "Run dummy search"}
                    </button>

                    <button
                        type="button"
                        onClick={handleRunDummySynthesis}
                        disabled={isSynthesisRunning}
                        className="inline-flex items-center rounded-md bg-app-accentSoft px-2.5 py-1 text-[11px] font-medium text-app-text transition hover:bg-app-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSynthesisRunning
                            ? "Generating dummy answer…"
                            : "Generate dummy answer"}
                    </button>

                    {/* Planner steps */}
                    <div className="mt-3 rounded-md border border-app-border bg-black/30 p-2">
                        <p className="text-[11px] font-semibold">
                            Planner steps
                        </p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Basic rule-based planner output (with optional LLM notes).
                        </p>

                        {selectedDetail.steps.filter(
                            (step) => step.step_type === "planner",
                        ).length === 0 ? (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No planner steps recorded.
                            </p>
                        ) : (
                            <ul className="mt-2 space-y-2">
                                {selectedDetail.steps
                                    .filter((step) => step.step_type === "planner")
                                    .map((step) => {
                                        const output = step.output ?? {};
                                        const subquestions: unknown[] = Array.isArray(
                                            (output as any).subquestions,
                                        )
                                            ? ((output as any).subquestions as unknown[])
                                            : [];

                                        return (
                                            <li
                                                key={step.id}
                                                className="rounded-md border border-app-border bg-black/50 p-2"
                                            >
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                                                    Planner step #{step.step_index}
                                                </p>
                                                {subquestions.length > 0 ? (
                                                    <ol className="mt-1 list-decimal space-y-1 pl-4 text-[11px]">
                                                        {subquestions.map((sq: unknown, idx: number) => (
                                                            <li key={idx}>{String(sq)}</li>
                                                        ))}
                                                    </ol>
                                                ) : (
                                                    <p className="mt-2 text-[11px] text-app-muted">
                                                        No subquestions found in planner output.
                                                    </p>
                                                )}
                                            </li>
                                        );
                                    })}
                            </ul>
                        )}
                    </div>

                    {/* Sources */}
                    <div className="mt-3 rounded-md border border-app-border bg-black/30 p-2">
                        <p className="text-[11px] font-semibold">
                            Sources (dummy)
                        </p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            These are placeholder sources from the dummy searcher agent. Real
                            web search will replace this later.
                        </p>

                        {selectedDetail.sources.length === 0 ? (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No sources attached yet. Run the dummy search to create some.
                            </p>
                        ) : (
                            <ul className="mt-2 space-y-2">
                                {selectedDetail.sources.map((source) => (
                                    <li
                                        key={source.id}
                                        className="rounded-md border border-app-border bg-black/50 p-2"
                                    >
                                        <a
                                            href={source.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="text-[11px] font-semibold text-app-accent hover:underline"
                                        >
                                            {source.title || source.url}
                                        </a>
                                        <p className="mt-1 text-[10px] text-app-muted">
                                            {source.summary ||
                                                "No summary available (dummy source placeholder)."}
                                        </p>
                                        <p className="mt-1 text-[10px] text-app-muted">
                                            Relevance:{" "}
                                            <span className="font-mono">
                                                {source.relevance_score ?? "n/a"}
                                            </span>
                                        </p>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {/* Answer */}
                    <div className="mt-3 rounded-md border border-app-border bg-black/30 p-2">
                        <p className="text-[11px] font-semibold">
                            Answer (dummy)
                        </p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            This synthesized answer is produced by the dummy synthesizer
                            agent. Later this will be powered by a real LLM and include
                            citations and deeper comparison.
                        </p>

                        {isSynthesisRunning && (
                            <p className="mt-2 text-[11px] text-app-muted">
                                Generating answer…
                            </p>
                        )}

                        {!isSynthesisRunning && (() => {
                            const answer = getSynthAnswer(selectedDetail);
                            if (!answer) {
                                return (
                                    <p className="mt-2 text-[11px] text-app-muted">
                                        No answer yet. Run the dummy synthesis to generate one.
                                    </p>
                                );
                            }

                            return (
                                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-black/60 p-2 text-[11px] text-app-text">
                                    {answer}
                                </pre>
                            );
                        })()}
                    </div>
                </div>
            )}
        </aside>
    );
}
