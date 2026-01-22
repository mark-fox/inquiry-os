import { apiPost } from "./client";

export interface ResearchRunCreate {
    query: string;
    title?: string | null;
}

export type ResearchRunStatus =
    | "pending"
    | "running"
    | "completed"
    | "failed";

export interface ResearchRunRead {
    id: string;
    query: string;
    title: string | null;
    status: ResearchRunStatus;
    model_provider: string;
    error_message: string | null;
    created_at: string;
    updated_at: string;
}

export type ResearchStepType =
    | "planner"
    | "searcher"
    | "reader"
    | "synthesizer";

export interface ResearchStepRead {
    id: string;
    run_id: string;
    step_index: number;
    step_type: ResearchStepType;
    input: Record<string, unknown> | null;
    output: Record<string, unknown> | null;
    created_at: string;
}

export interface ResearchRunDetail extends ResearchRunRead {
    steps: ResearchStepRead[];
}

export async function createResearchRun(
    payload: ResearchRunCreate,
): Promise<ResearchRunRead> {
    return apiPost<ResearchRunCreate, ResearchRunRead>("/research-runs", payload);
}

export async function getResearchRunDetail(
    runId: string,
): Promise<ResearchRunDetail> {
    const url = `/research-runs/${runId}/detail`;
    const baseUrl =
        import.meta.env.VITE_API_BASE_URL?.toString() ||
        "http://localhost:8000/api/v1";

    const res = await fetch(`${baseUrl}${url}`, {
        method: "GET",
    });

    if (!res.ok) {
        let message = `Request failed with status ${res.status}`;

        try {
            const data = await res.json();
            if (data && typeof data.detail === "string") {
                message = data.detail;
            }
        } catch {
            // ignore JSON parse error
        }

        throw new Error(message);
    }

    return (await res.json()) as ResearchRunDetail;
}


export async function listResearchRuns(
    limit = 10,
    offset = 0,
): Promise<ResearchRunRead[]> {
    const baseUrl =
        import.meta.env.VITE_API_BASE_URL?.toString() ||
        "http://localhost:8000/api/v1";

    const url = `${baseUrl}/research-runs?limit=${limit}&offset=${offset}`;

    const res = await fetch(url, {
        method: "GET",
    });

    if (!res.ok) {
        let message = `Request failed with status ${res.status}`;

        try {
            const data = await res.json();
            if (data && typeof data.detail === "string") {
                message = data.detail;
            }
        } catch {
            // ignore JSON parse error
        }

        throw new Error(message);
    }

    return (await res.json()) as ResearchRunRead[];
}
