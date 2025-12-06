
const API_BASE = process.env.REACT_APP_API_BASE_URL || "https://backend-737530900569.europe-west2.run.app";
export async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });

    if (!res.ok) {
        const errorData = await res.text();
        throw new Error(`API error (${res.status}): ${errorData}`);
    }

    return res.json();
}
