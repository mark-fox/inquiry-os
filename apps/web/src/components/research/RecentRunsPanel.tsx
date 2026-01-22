import { useEffect, useState } from "react";
import type { ResearchRunRead } from "../../api/research";
import { listResearchRuns } from "../../api/research";

function formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}

export function RecentRunsPanel() {
    const [runs, setRuns] = useState<ResearchRunRead[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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
                    {runs.map((run) => (
                        <li
                            key={run.id}
                            className="rounded-lg border border-app-border bg-black/30 p-3"
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
                    ))}
                </ul>
            )}
        </aside>
    );
}
