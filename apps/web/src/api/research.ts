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

export async function createResearchRun(
    payload: ResearchRunCreate,
): Promise<ResearchRunRead> {
    return apiPost<ResearchRunCreate, ResearchRunRead>("/research-runs", payload);
}
