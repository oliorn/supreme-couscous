import { apiFetch } from "./client";

export async function scrapeWebsite(url) {
  if (!url) throw new Error("Missing URL");
  return apiFetch(`/scrape?url=${encodeURIComponent(url)}`);
}

// load from bakcend companies
export async function fetchCompanies() {
  return apiFetch("/companies");
}