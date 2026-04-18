import type { FormEvent } from "react";
import { useState } from "react";
import { createResearchRun } from "../../api/research";

type NewResearchRunFormProps = {
    onRunCreated?: (runId: string) => void;
};

export function NewResearchRunForm({ onRunCreated }: NewResearchRunFormProps) {
    const [title, setTitle] = useState("");
    const [query, setQuery] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!query.trim()) {
            setError("Please enter a research question.");
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            const run = await createResearchRun({
                query: query.trim(),
                title: title.trim() || null,
            });

            onRunCreated?.(run.id);

        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Failed to create research run.";
            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="rounded-xl border border-app-border bg-app-surface p-5 shadow-soft">
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
        </div>
    );
}
