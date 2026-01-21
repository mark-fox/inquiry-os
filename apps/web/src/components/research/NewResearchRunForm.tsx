import type { FormEvent } from "react";
import { useState } from "react";
import {
    createResearchRun,
    getResearchRunDetail,
    type ResearchRunDetail,
} from "../../api/research";

export function NewResearchRunForm() {
    const [title, setTitle] = useState("");
    const [query, setQuery] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [detail, setDetail] = useState<ResearchRunDetail | null>(null);

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!query.trim()) {
            setError("Please enter a research question.");
            return;
        }

        setIsSubmitting(true);
        setError(null);
        setDetail(null);

        try {
            const run = await createResearchRun({
                query: query.trim(),
                title: title.trim() || null,
            });

            // Fetch the detail view so we can see planner steps
            const fullDetail = await getResearchRunDetail(run.id);
            setDetail(fullDetail);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to create research run.";
            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="rounded-xl border border-app-border bg-app-surface p-6 shadow-soft">
            <h2 className="text-lg font-medium">New Research Run</h2>
            <p className="mt-2 text-sm text-app-muted">
                Start with a complex research question. InquiryOS will eventually plan,
                search, read, and synthesize an answer for you.
            </p>

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                <div className="space-y-1">
                    <label
                        htmlFor="title"
                        className="block text-sm font-medium text-app-muted"
                    >
                        Title (optional)
                    </label>
                    <input
                        id="title"
                        type="text"
                        className="w-full rounded-lg border border-app-border bg-app-bg px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
                        placeholder="e.g. Vector DB comparison for small-team RAG"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                    />
                </div>

                <div className="space-y-1">
                    <label
                        htmlFor="query"
                        className="block text-sm font-medium text-app-muted"
                    >
                        Research question
                    </label>
                    <textarea
                        id="query"
                        rows={5}
                        className="w-full rounded-lg border border-app-border bg-app-bg px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
                        placeholder="Compare pgvector, Qdrant, and Weaviate for a small-team internal RAG system..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                </div>

                <div className="flex items-center gap-3">
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="inline-flex items-center rounded-lg bg-app-accent px-4 py-2 text-sm font-medium text-app-bg transition hover:bg-app-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? "Creating run…" : "Run research"}
                    </button>

                    {error && (
                        <p className="text-sm text-red-400">
                            {error}
                        </p>
                    )}
                </div>
            </form>

            {detail && (
                <div className="mt-6 space-y-4">
                    <div className="rounded-lg border border-app-border bg-app-bg/60 p-4">
                        <h3 className="text-sm font-semibold">
                            Run created
                        </h3>
                        <p className="mt-1 text-xs text-app-muted">
                            ID: <span className="font-mono">{detail.id}</span>
                        </p>
                        <p className="mt-1 text-xs text-app-muted">
                            Status:{" "}
                            <span className="font-semibold text-app-accent">
                                {detail.status}
                            </span>
                        </p>
                        <p className="mt-1 text-xs text-app-muted">
                            Model: <span className="font-mono">{detail.model_provider}</span>
                        </p>
                    </div>

                    <div className="rounded-lg border border-app-border bg-app-bg/60 p-4">
                        <h3 className="text-sm font-semibold">
                            Planner steps
                        </h3>
                        <p className="mt-1 text-xs text-app-muted">
                            Showing the basic rule-based plan (no LLM yet).
                        </p>

                        {detail.steps.length === 0 ? (
                            <p className="mt-3 text-sm text-app-muted">
                                No steps recorded yet.
                            </p>
                        ) : (
                            <ul className="mt-3 space-y-3">
                                {detail.steps
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
                                                className="rounded-md border border-app-border bg-black/30 p-3"
                                            >
                                                <p className="text-xs font-semibold uppercase tracking-wide text-app-muted">
                                                    Planner step #{step.step_index}
                                                </p>
                                                {subquestions.length > 0 ? (
                                                    <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                                                        {subquestions.map((sq: unknown, idx: number) => (
                                                            <li key={idx}>{String(sq)}</li>
                                                        ))}
                                                    </ol>
                                                ) : (
                                                    <p className="mt-2 text-sm text-app-muted">
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
        </div>
    );
}
