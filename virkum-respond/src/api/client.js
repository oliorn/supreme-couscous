
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:4001";

export async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
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
