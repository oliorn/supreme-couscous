import { apiFetch } from "./client";

export async function scrapeWebsite(url) {
  if (!url) throw new Error("Missing URL");
  return apiFetch(`/scrape?url=${encodeURIComponent(url)}`);
}
