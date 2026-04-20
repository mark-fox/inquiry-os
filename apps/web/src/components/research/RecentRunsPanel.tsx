import { useEffect, useState } from "react";
import type {
    ResearchRunRead,
    ResearchRunDetail,
    ResearchRunState,
} from "../../api/research";
import {
    listResearchRuns,
    getResearchRunDetail,
    getResearchRunState,
    executePipeline,
} from "../../api/research";
import { RecentRunsList } from "./RecentRunsList";
import { SelectedRunWorkspace } from "./SelectedRunWorkspace";

type RecentRunsPanelProps = {
    autoRunId?: string | null;
};

export function RecentRunsPanel({ autoRunId }: RecentRunsPanelProps) {
    const [runs, setRuns] = useState<ResearchRunRead[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDetail, setSelectedDetail] = useState<ResearchRunDetail | null>(null);
    const [isDetailLoading, setIsDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState<string | null>(null);

    const [runState, setRunState] = useState<ResearchRunState | null>(null);
    const [isStateLoading, setIsStateLoading] = useState(false);

    const [isExecuteRunning, setIsExecuteRunning] = useState(false);

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

    useEffect(() => {
        if (!autoRunId) return;

        const runId = autoRunId;
        let cancelled = false;

        async function autoRunNewResearch() {
            setIsDetailLoading(true);
            setIsExecuteRunning(true);
            setDetailError(null);

            try {
                const detail = await getResearchRunDetail(runId);
                if (cancelled) return;
                setSelectedDetail(detail);

                const refreshedRuns = await listResearchRuns(10, 0);
                if (cancelled) return;
                setRuns(refreshedRuns);

                await executePipeline(runId, "real");
                if (cancelled) return;

                await pollRunUntilFinished(runId);
            } catch (err) {
                if (cancelled) return;
                const message =
                    err instanceof Error ? err.message : "Failed to auto-run pipeline.";
                setDetailError(message);
            } finally {
                if (!cancelled) {
                    setIsDetailLoading(false);
                    setIsExecuteRunning(false);
                }
            }
        }

        autoRunNewResearch();

        return () => {
            cancelled = true;
        };
    }, [autoRunId]);

    useEffect(() => {
        if (!selectedDetail) return;

        const interval = setInterval(async () => {
            try {
                const state = await getResearchRunState(selectedDetail.id);
                setRunState(state);

                if (state.status === "completed" || state.status === "failed") {
                    clearInterval(interval);
                }
            } catch {
                // ignore transient errors
            }
        }, 1500);

        return () => clearInterval(interval);
    }, [selectedDetail?.id]);

    async function handleSelectRun(runId: string) {
        setIsDetailLoading(true);
        setDetailError(null);

        try {
            const detail = await getResearchRunDetail(runId);
            setSelectedDetail(detail);

            setIsStateLoading(true);
            const state = await getResearchRunState(runId);
            setRunState(state);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to load run details.";
            setDetailError(message);
        } finally {
            setIsDetailLoading(false);
            setIsStateLoading(false);
        }
    }

    async function pollRunUntilFinished(runId: string) {
        const maxAttempts = 20;
        const delayMs = 1500;

        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
            const state = await getResearchRunState(runId);
            setRunState(state);

            if (state.status === "completed" || state.status === "failed") {
                const detail = await getResearchRunDetail(runId);
                setSelectedDetail(detail);

                const refreshedRuns = await listResearchRuns(10, 0);
                setRuns(refreshedRuns);
                return;
            }

            await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
    }

    async function handleExecutePipeline() {
        if (!selectedDetail) return;

        setIsExecuteRunning(true);
        setDetailError(null);

        try {
            await executePipeline(selectedDetail.id, "real");
            await pollRunUntilFinished(selectedDetail.id);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to execute pipeline.";
            setDetailError(message);
        } finally {
            setIsExecuteRunning(false);
        }
    }

    async function handleRetryReal() {
        if (!selectedDetail) return;

        setIsExecuteRunning(true);
        setDetailError(null);

        try {
            await executePipeline(selectedDetail.id, "real");
            await pollRunUntilFinished(selectedDetail.id);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to retry pipeline.";
            setDetailError(message);
        } finally {
            setIsExecuteRunning(false);
        }
    }

    return (
        <div className="grid gap-6 lg:grid-cols-[320px,minmax(0,1fr)]">
            <RecentRunsList
                runs={runs}
                isLoading={isLoading}
                error={error}
                selectedRunId={selectedDetail?.id ?? null}
                onSelectRun={handleSelectRun}
            />

            <SelectedRunWorkspace
                selectedDetail={selectedDetail}
                isDetailLoading={isDetailLoading}
                detailError={detailError}
                runState={runState}
                isStateLoading={isStateLoading}
                isExecuteRunning={isExecuteRunning}
                onRunPipeline={handleExecutePipeline}
                onRetryReal={handleRetryReal}
            />
        </div>
    );
}