const API_BASE = process.env.REACT_APP_API_BASE_URL || "https://backend-737530900569.europe-west2.run.app";

export async function fetchTests(limit = 50) {
  const res = await fetch(`${API_BASE}/tests?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch tests: ${res.status}`);
  }
  return res.json();
}