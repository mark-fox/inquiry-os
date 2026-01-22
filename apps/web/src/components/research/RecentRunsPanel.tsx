import { useEffect, useState } from "react";
import type { ResearchRunRead, ResearchRunDetail } from "../../api/research";
import { listResearchRuns, getResearchRunDetail } from "../../api/research";

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
                </div>
            )}
        </aside>
    );
}
