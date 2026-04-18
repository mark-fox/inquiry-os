import type { ResearchRunRead } from "../../api/research";

function formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}

type RecentRunsListProps = {
    runs: ResearchRunRead[];
    isLoading: boolean;
    error: string | null;
    selectedRunId: string | null;
    onSelectRun: (runId: string) => void;
};

export function RecentRunsList({
    runs,
    isLoading,
    error,
    selectedRunId,
    onSelectRun,
}: RecentRunsListProps) {
    return (
        <div className="rounded-xl border border-app-border bg-app-surface p-4 shadow-soft">
            <h2 className="text-sm font-semibold">Recent runs</h2>
            <p className="mt-1 text-xs text-app-muted">
                Latest research runs in this workspace.
            </p>

            <div className="mt-3 max-h-[900px] overflow-y-auto pr-1">
                {isLoading && (
                    <p className="text-sm text-app-muted">Loading…</p>
                )}

                {error && (
                    <p className="text-sm text-red-400">{error}</p>
                )}

                {!isLoading && !error && runs.length === 0 && (
                    <p className="text-sm text-app-muted">
                        No runs yet. Create a new research run to get started.
                    </p>
                )}

                {!isLoading && !error && runs.length > 0 && (
                    <ul className="space-y-2">
                        {runs.map((run) => {
                            const isSelected = selectedRunId === run.id;

                            return (
                                <li
                                    key={run.id}
                                    onClick={() => onSelectRun(run.id)}
                                    className={`rounded-lg border bg-black/30 p-3 text-left transition ${isSelected
                                            ? "border-app-accent bg-black/40"
                                            : "cursor-pointer border-app-border hover:border-app-accent/60 hover:bg-black/40"
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
            </div>
        </div>
    );
}