import { apiFetch } from "./client";

export async function scrapeWebsite(url) {
  if (!url) throw new Error("Missing URL");

  const res = await apiFetch(`/scrape?url=${encodeURIComponent(url)}`);

  return res;
}
