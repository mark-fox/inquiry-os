import { useState } from "react";

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

function getSourceDomain(url: string): string {
    try {
        const parsed = new URL(url);
        return parsed.hostname.replace(/^www\./, "");
    } catch {
        return url;
    }
}

function getSourceRankingHints(
    source: {
        title: string;
        summary: string | null;
        raw_content: string | null;
    },
    query: string,
    wasUsedInSynthesis: boolean,
): string[] {
    const queryTerms = Array.from(
        new Set(
            query
                .toLowerCase()
                .match(/\w+/g)
                ?.filter((term) => term.length >= 3) ?? [],
        ),
    );

    const titleText = (source.title || "").toLowerCase();
    const summaryText = (source.summary || "").toLowerCase();
    const rawText = (source.raw_content || "").toLowerCase();

    let titleMatches = 0;
    let summaryMatches = 0;
    let rawMatches = 0;

    for (const term of queryTerms) {
        if (titleText.includes(term)) titleMatches += 1;
        if (summaryText.includes(term)) summaryMatches += 1;
        if (rawText.includes(term)) rawMatches += 1;
    }

    const hints: string[] = [];

    if (titleMatches >= 2) {
        hints.push("strong title match");
    } else if (titleMatches === 1) {
        hints.push("title matches query");
    }

    if (summaryMatches >= 2) {
        hints.push("query terms found in summary");
    } else if (summaryMatches === 1) {
        hints.push("summary overlaps with query");
    }

    if (rawMatches >= 3) {
        hints.push("deeper content overlap");
    }

    if (wasUsedInSynthesis) {
        hints.push("used in synthesis");
    }

    return hints.slice(0, 3);
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
    const [showExecutionHistory, setShowExecutionHistory] = useState(false);
    const [showPlannerSteps, setShowPlannerSteps] = useState(false);

    if (isDetailLoading && !selectedDetail) {
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

    const synthOutput = getSynthOutput(selectedDetail);

    const synthesisMeta =
        synthOutput &&
            typeof (synthOutput as any)._meta === "object" &&
            (synthOutput as any)._meta !== null
            ? ((synthOutput as any)._meta as Record<string, unknown>)
            : null;

    const usedSourceIds =
        synthesisMeta && Array.isArray((synthesisMeta as any).used_source_ids)
            ? new Set(
                ((synthesisMeta as any).used_source_ids as unknown[]).map((id) =>
                    String(id),
                ),
            )
            : new Set<string>();

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
                        <button
                            type="button"
                            onClick={() => setShowExecutionHistory((v) => !v)}
                            className="flex w-full items-center justify-between text-left"
                        >
                            <span className="text-[11px] font-semibold">Execution history</span>
                            <span className="text-[10px] text-app-muted">
                                {showExecutionHistory ? "Hide" : "Show"}
                            </span>
                        </button>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Audit trail of pipeline runs.
                        </p>

                        {showExecutionHistory && (
                            <>
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
                            </>
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
                                    const isRunning = s.status === "running";
                                    const isCompleted = s.status === "completed";
                                    const isFailed = s.status === "failed";
                                    return (
                                        <li
                                            key={t}
                                            className={`flex items-center justify-between rounded px-2 py-1 ${isRunning
                                                ? "bg-app-accent/20 border border-app-accent/40"
                                                : ""
                                                }`}
                                        >
                                            <span className="flex items-center gap-2">
                                                <span className="font-semibold">
                                                    {t.charAt(0).toUpperCase() + t.slice(1)}:
                                                </span>

                                                {isRunning && (
                                                    <span className="text-[10px] text-app-accent animate-pulse">
                                                        running…
                                                    </span>
                                                )}

                                                {isCompleted && (
                                                    <span className="text-[10px] text-green-400">
                                                        completed
                                                    </span>
                                                )}

                                                {isFailed && (
                                                    <span className="text-[10px] text-red-400">
                                                        failed
                                                    </span>
                                                )}

                                                {s.status === "pending" && (
                                                    <span className="text-[10px] text-app-muted">
                                                        pending
                                                    </span>
                                                )}
                                            </span>

                                            {s.error_message && (
                                                <span className="ml-2 text-red-400 text-[10px]">
                                                    {s.error_message}
                                                </span>
                                            )}
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
                        <button
                            type="button"
                            onClick={() => setShowPlannerSteps((v) => !v)}
                            className="flex w-full items-center justify-between text-left"
                        >
                            <span className="text-[11px] font-semibold">Planner steps</span>
                            <span className="text-[10px] text-app-muted">
                                {showPlannerSteps ? "Hide" : "Show"}
                            </span>
                        </button>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Initial plan generated for this research run.
                        </p>

                        {showPlannerSteps && (
                            <>
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
                            </>
                        )}
                    </div>
                </>

                <>
                    <div className="rounded-md border border-app-border bg-black/30 p-3">
                        <p className="text-[11px] font-semibold">Sources</p>
                        <p className="mt-1 text-[10px] text-app-muted">
                            Sources collected for this run, ranked by relevance, with simple hints showing why they ranked well.
                        </p>

                        {selectedDetail.sources.length === 0 ? (
                            <p className="mt-2 text-[11px] text-app-muted">
                                No sources attached yet. Run the pipeline to collect sources.
                            </p>
                        ) : (
                            <ul className="mt-2 max-h-[420px] space-y-2 overflow-y-auto pr-1">
                                {[...selectedDetail.sources]
                                    .sort((a, b) => {
                                        const aScore = typeof a.relevance_score === "number" ? a.relevance_score : -1;
                                        const bScore = typeof b.relevance_score === "number" ? b.relevance_score : -1;
                                        return bScore - aScore;
                                    })
                                    .map((source, idx) => {
                                        const domain = getSourceDomain(source.url);
                                        const wasUsedInSynthesis = usedSourceIds.has(source.id);
                                        const rankingHints = getSourceRankingHints(
                                            source,
                                            selectedDetail.query,
                                            wasUsedInSynthesis,
                                        );
                                        const summary =
                                            source.summary && source.summary.trim().length > 0
                                                ? source.summary
                                                : "No summary available.";

                                        return (
                                            <li
                                                key={source.id}
                                                className="rounded-md border border-app-border bg-black/50 p-3"
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div className="min-w-0">
                                                        <div className="flex flex-wrap items-center gap-2">
                                                            <span className="rounded bg-app-bg px-1.5 py-0.5 font-mono text-[10px] text-app-accent">
                                                                [{idx + 1}]
                                                            </span>

                                                            <span className="text-[10px] text-app-muted">
                                                                {domain}
                                                            </span>

                                                            {rankingHints.map((hint, hintIdx) => (
                                                                <span
                                                                    key={hintIdx}
                                                                    className="rounded bg-app-bg/70 px-1.5 py-0.5 text-[10px] text-app-muted"
                                                                >
                                                                    {hint}
                                                                </span>
                                                            ))}
                                                        </div>

                                                        <a
                                                            href={source.url}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                            className="mt-1 block text-[11px] font-semibold text-app-accent hover:underline"
                                                        >
                                                            {source.title || source.url}
                                                        </a>
                                                    </div>

                                                    <div className="shrink-0 text-right">
                                                        <p className="text-[10px] text-app-muted">Relevance</p>
                                                        <p className="font-mono text-[11px] text-app-text">
                                                            {typeof source.relevance_score === "number"
                                                                ? source.relevance_score.toFixed(1)
                                                                : "n/a"}
                                                        </p>
                                                    </div>
                                                </div>

                                                <p className="mt-2 line-clamp-4 text-[10px] leading-5 text-app-muted">
                                                    {summary}
                                                </p>
                                            </li>
                                        );
                                    })}
                            </ul>
                        )}
                    </div>


                </>
            </div>
        </div>
    );
}