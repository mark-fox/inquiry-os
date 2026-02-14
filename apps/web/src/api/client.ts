const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL?.toString() || DEFAULT_API_BASE_URL;

async function handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
        let message = `Request failed with status ${res.status}`;

        try {
            const data = await res.json();
            if (data && typeof data.detail === "string") {
                message = data.detail;
            }
        } catch {
            // ignore JSON parse error, keep default message
        }

        throw new Error(message);
    }

    return (await res.json()) as T;
}

export async function apiPost<TBody, TResponse>(
    path: string,
    body: TBody,
): Promise<TResponse> {
    const url = `${API_BASE_URL}${path}`;

    const res = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });

    return handleResponse<TResponse>(res);
}

export async function apiGet<TResponse>(path: string): Promise<TResponse> {
  const url = `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  return handleResponse<TResponse>(res);
}