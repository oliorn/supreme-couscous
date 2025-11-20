import { apiFetch } from "./client";

export async function generateEmail(companyName, topic = null) {
  return apiFetch("/llm/generate-email", {
    method: "POST",
    body: JSON.stringify({
      company_name: companyName,
      topic,
      // þú getur bætt við language/tone hér ef þú vilt
    }),
  });
}
