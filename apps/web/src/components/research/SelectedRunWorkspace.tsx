import type {
    ResearchRunDetail,
    ResearchRunState,
    ResearchStepType,
} from "../../api/research";

function getLatestFailureMessage(detail: ResearchRunDetail | null): string | null {
    if (!detail?.events?.length) return null;

    const latestFailed = detail.events
        .slice()
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
        .find((e) => e.event_type === "failed" && e.error_message);

    return latestFailed?.error_message ?? null;
}

function getSynthOutput(detail: ResearchRunDetail | null): Record<string, unknown> | null {
    if (!detail?.answer?.content) return null;

    try {
        return JSON.parse(detail.answer.content) as Record<string, unknown>;
    } catch {
        return null;
    }
}

function renderTextWithCitations(
    text: string,
    sources: { url: string; title: string }[],
) {
    const parts = text.split(/(\[\d+\])/g);

    return parts.map((part, idx) => {
        const match = part.match(/^\[(\d+)\]$/);

        if (!match) {
            return <span key={idx}>{part}</span>;
        }

        const sourceIndex = Number(match[1]) - 1;
        const source = sources[sourceIndex];

        if (!source) {
            return (
                <span key={idx} className="font-mono text-app-muted">
                    {part}
                </span>
            );
        }

        return (
            <a
                key={idx}
                href={source.url}
                target="_blank"
                rel="noreferrer"
                title={source.title || source.url}
                className="font-mono text-app-accent hover:underline"
            >
                {part}
            </a>
        );
    });
}

type SelectedRunWorkspaceProps = {
    selectedDetail: ResearchRunDetail | null;
    isDetailLoading: boolean;
    detailError: string | null;
    runState: ResearchRunState | null;
    isStateLoading: boolean;
    isExecuteRunning: boolean;
    onRunPipeline: () => void;
    onRetryReal: () => void;
};

export function SelectedRunWorkspace({
    selectedDetail,
    isDetailLoading,
    detailError,
    runState,
    isStateLoading,
    isExecuteRunning,
    onRunPipeline,
    onRetryReal,
}: SelectedRunWorkspaceProps) {
    if (isDetailLoading) {
        return (
            <div className="rounded-xl border border-app-border bg-app-surface p-4 shadow-soft">
                <p className="text-sm text-app-muted">Loading selected run…</p>
            </div>
        );
    }

    if (detailError) {
        return (
            <div className="rounded-xl border border-app-border bg-app-surface p-4 shadow-soft">
                <p className="text-sm text-red-400">{detailError}</p>
            </div>
        );
    }

    if (!selectedDetail) {
        return (
            <div className="rounded-xl border border-app-border bg-app-surface p-6 shadow-soft">
                <h2 className="text-lg font-semibold">Research workspace</h2>
                <p className="mt-2 text-sm text-app-muted">
                    Select a run from the left or create a new one to see its pipeline,
                    sources, and synthesized answer.
                </p>
            </div>
        );
    }

    return (
        <div className="rounded-xl border border-app-border bg-app-surface p-4 shadow-soft">
            <h2 className="text-lg font-semibold">Selected run</h2>
            <p className="mt-2 text-sm text-app-text">
                {selectedDetail.title || "Untitled run"}
            </p>
            <p className="mt-1 text-sm text-app-muted">{selectedDetail.query}</p>

            <p className="mt-3 text-[11px] text-app-muted">
                Status:{" "}
                <span className="font-semibold text-app-accent">
                    {selectedDetail.status}
                </span>
            </p>

            {(() => {
                const msg = getLatestFailureMessage(selectedDetail);
                if (!msg) return null;

                return (
                    <p className="mt-2 text-[11px] text-red-400">
                        Last failure: <span className="font-mono">{msg}</span>
                    </p>
                );
            })()}

            <p className="mt-1 text-[11px] text-app-muted">
                Model:{" "}
                <span className="font-mono">
                    {selectedDetail.model_provider.replace("dummy:", "").replace("ollama:", "ollama / ")}
                </span>
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
                <button
                    type="button"
                    onClick={onRunPipeline}
                    disabled={isExecuteRunning}
                    className="inline-flex items-center rounded-md bg-app-accent px-3 py-1.5 text-[12px] font-medium text-app-bg transition hover:bg-app-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {isExecuteRunning ? "Running pipeline…" : "Run pipeline"}
                </button>

                {selectedDetail.status === "failed" && (
                    <button
                        type="button"
                        onClick={onRetryReal}
                        disabled={isExecuteRunning}
                        className="inline-flex items-center rounded-md bg-red-500/80 px-3 py-1.5 text-[12px] font-medium text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isExecuteRunning ? "Retrying…" : "Retry (real)"}
                    </button>
                )}
            </div>

            <div className="rounded-lg border border-app-accent/40 bg-black/40 p-4 shadow-md">
                <p className="text-[11px] font-semibold">Answer</p>
                <p className="mt-1 text-[10px] text-app-muted">
                    This answer was generated by the synthesis stage using the collected sources.
                </p>

                {isExecuteRunning && (
                    <p className="mt-2 text-[11px] text-app-muted">Generating answer…</p>
                )}

                {!isExecuteRunning && (() => {
                    const out = getSynthOutput(selectedDetail);

                    const synthStep = selectedDetail.steps.find(
                        (s) => s.step_type === "synthesizer"
                    );

                    const synthFailed =
                        synthStep?.status === "failed" && !!synthStep.error_message;

                    if (!out) {
                        if (synthFailed) {
                            return (
                                <div className="mt-2 rounded-md border border-red-500/40 bg-red-500/10 p-2 text-[11px] text-red-300">
                                    <p className="font-semibold">Synthesis failed</p>
                                    <p className="mt-1">
                                        {synthStep?.error_message || "Unknown error occurred during synthesis."}
                                    </p>
                                </div>
                            );
                        }

                        return (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No answer yet. Run the pipeline to generate one.
                            </p>
                        );
                    }

                    const summary = typeof out.summary === "string" ? out.summary : "";
                    const recommendation =
                        typeof out.recommendation === "string" ? out.recommendation : "";
                    const confidence = typeof out.confidence === "number" ? out.confidence : null;

                    const keyPoints = Array.isArray(out.key_points) ? out.key_points : [];
                    const risks = Array.isArray(out.risks) ? out.risks : [];

                    const meta =
                        out && typeof (out as any)._meta === "object" && (out as any)._meta !== null
                            ? ((out as any)._meta as Record<string, unknown>)
                            : null;

                    const warnings = Array.isArray((out as any)._warnings) ? ((out as any)._warnings as unknown[]) : [];

                    const coverageRatio = meta && typeof meta.coverage_ratio === "number" ? meta.coverage_ratio : null;
                    const uniqueSourcesCited =
                        meta && typeof meta.unique_sources_cited === "number" ? meta.unique_sources_cited : null;

                    const totalSources = selectedDetail.sources.length;

                    return (
                        <div className="mt-2 space-y-3 text-[11px]">
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                                    Summary
                                </p>
                                <p className="mt-1 text-app-text">
                                    {summary ? renderTextWithCitations(summary, selectedDetail.sources) : "—"}
                                </p>
                            </div>

                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                                    Key points
                                </p>
                                {keyPoints.length === 0 ? (
                                    <p className="mt-1 text-app-muted">—</p>
                                ) : (
                                    <ul className="mt-1 list-disc space-y-1 pl-4">
                                        {keyPoints.map((p: unknown, idx: number) => (
                                            <li key={idx}>
                                                {renderTextWithCitations(String(p), selectedDetail.sources)}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>

                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                                    Risks
                                </p>
                                {risks.length === 0 ? (
                                    <p className="mt-1 text-app-muted">—</p>
                                ) : (
                                    <ul className="mt-1 list-disc space-y-1 pl-4">
                                        {risks.map((r: unknown, idx: number) => (
                                            <li key={idx}>
                                                {renderTextWithCitations(String(r), selectedDetail.sources)}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>

                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                                    Recommendation
                                </p>
                                <p className="mt-1 text-app-text">
                                    {recommendation
                                        ? renderTextWithCitations(recommendation, selectedDetail.sources)
                                        : "—"}
                                </p>
                            </div>

                            <div className="text-[10px] text-app-muted">
                                Confidence:{" "}
                                <span className="font-mono text-app-text">
                                    {confidence === null ? "n/a" : confidence.toFixed(2)}
                                </span>
                            </div>

                            <div className="rounded-md border border-app-border bg-black/40 p-2">
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-app-muted">
                                    Synthesis quality
                                </p>

                                <div className="mt-2 space-y-1 text-[11px] text-app-muted">
                                    <p>
                                        Coverage:{" "}
                                        <span className="font-mono text-app-text">
                                            {coverageRatio === null ? "n/a" : `${Math.round(coverageRatio * 100)}%`}
                                        </span>
                                    </p>

                                    <p>
                                        Unique sources cited:{" "}
                                        <span className="font-mono text-app-text">
                                            {uniqueSourcesCited === null ? "n/a" : `${uniqueSourcesCited} / ${totalSources}`}
                                        </span>
                                    </p>

                                    {warnings.length > 0 && (
                                        <div className="mt-2">
                                            <p className="text-[11px] font-semibold text-yellow-300">Warnings</p>
                                            <ul className="mt-1 list-disc space-y-1 pl-4">
                                                {warnings.slice(0, 5).map((w: unknown, idx: number) => {
                                                    if (typeof w === "string") {
                                                        return (
                                                            <li key={idx} className="break-words">
                                                                {w}
                                                            </li>
                                                        );
                                                    }

                                                    if (typeof w === "object" && w !== null) {
                                                        const warning = w as Record<string, unknown>;
                                                        const type = typeof warning.type === "string" ? warning.type : "unknown_warning";

                                                        if (type === "missing_citations") {
                                                            const fields = Array.isArray(warning.fields)
                                                                ? warning.fields.map((f) => String(f)).join(", ")
                                                                : "unknown fields";

                                                            return (
                                                                <li key={idx} className="break-words">
                                                                    Some synthesis items are missing citations: {fields}.
                                                                </li>
                                                            );
                                                        }

                                                        if (type === "low_source_coverage") {
                                                            const ratio =
                                                                typeof warning.coverage_ratio === "number"
                                                                    ? `${Math.round(warning.coverage_ratio * 100)}%`
                                                                    : "unknown";

                                                            return (
                                                                <li key={idx} className="break-words">
                                                                    Source coverage is low ({ratio} of available sources cited).
                                                                </li>
                                                            );
                                                        }

                                                        return (
                                                            <li key={idx} className="break-words">
                                                                {type}
                                                            </li>
                                                        );
                                                    }

                                                    return (
                                                        <li key={idx} className="break-words">
                                                            Unknown warning
                                                        </li>
                                                    );
                                                })}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })()}
            </div>

            <div className="mt-4 space-y-4">
                <>
                    <div className="rounded-md border border-app-border bg-black/30 p-3">
                        <p className="text-[11px] font-semibold">Execution history</p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Audit trail of pipeline runs.
                        </p>

                        {selectedDetail.events?.length ? (
                            <ul className="mt-2 space-y-1 text-[11px]">
                                {selectedDetail.events
                                    .slice()
                                    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
                                    .slice(0, 8)
                                    .map((ev) => (
                                        <li key={ev.id} className="flex items-center justify-between">
                                            <span className="text-app-text">
                                                <span className="font-semibold">{ev.event_type}</span>{" "}
                                                <span className="text-app-muted">({ev.mode})</span>
                                            </span>
                                            <span className="text-[10px] text-app-muted">
                                                {ev.duration_ms != null ? `${ev.duration_ms}ms` : "—"}
                                            </span>
                                        </li>
                                    ))}
                            </ul>
                        ) : (
                            <p className="mt-2 text-[11px] text-app-muted">No execution events yet.</p>
                        )}
                    </div>

                    <div className="rounded-md border border-app-border bg-black/30 p-3">
                        <p className="text-[11px] font-semibold">Pipeline status</p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Live pipeline state from the backend.
                        </p>

                        {isStateLoading && (
                            <p className="mt-2 text-[11px] text-app-muted">Loading pipeline state…</p>
                        )}

                        {!isStateLoading && !runState && (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No pipeline state loaded yet.
                            </p>
                        )}

                        {!isStateLoading && runState && (
                            <ul className="mt-2 space-y-1 text-[11px]">
                                {(["planner", "searcher", "reader", "synthesizer"] as ResearchStepType[]).map((t) => {
                                    const s = runState.steps[t];
                                    return (
                                        <li key={t}>
                                            <span className="font-semibold">
                                                {t.charAt(0).toUpperCase() + t.slice(1)}:
                                            </span>{" "}
                                            <span className="text-app-muted">{s.status}</span>
                                            {s.error_message ? (
                                                <span className="ml-2 text-red-400">({s.error_message})</span>
                                            ) : null}
                                        </li>
                                    );
                                })}
                                <li className="pt-2 text-[10px] text-app-muted">
                                    Sources: {runState.source_count} • Summarized: {runState.sources_with_summary}
                                </li>
                            </ul>
                        )}
                    </div>

                    <div className="rounded-md border border-app-border bg-black/30 p-3">
                        <p className="text-[11px] font-semibold">Planner steps</p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Initial plan generated for this research run.
                        </p>

                        {selectedDetail.steps.filter((step) => step.step_type === "planner").length === 0 ? (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No planner steps recorded.
                            </p>
                        ) : (
                            <ul className="mt-2 space-y-2">
                                {selectedDetail.steps
                                    .filter((step) => step.step_type === "planner")
                                    .map((step) => {
                                        const output = step.output ?? {};
                                        const subquestions: unknown[] = Array.isArray((output as any).subquestions)
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
                </>

                <>
                    <div className="rounded-md border border-app-border bg-black/30 p-3">
                        <p className="text-[11px] font-semibold">Sources</p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Sources collected for this research run and used by the pipeline.
                        </p>

                        {selectedDetail.sources.length === 0 ? (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No sources attached yet. Run the pipeline to collect sources.
                            </p>
                        ) : (
                            <ul className="mt-2 max-h-[420px] space-y-2 overflow-y-auto pr-1">
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
                                            {source.summary || "No summary available."}
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


                </>
            </div>
        </div>
    );
}