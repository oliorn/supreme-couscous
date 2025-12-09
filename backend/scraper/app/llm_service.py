# app/llm_service.py
import os, time, re, json
from openai import OpenAI
from fastapi import HTTPException

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = "gpt-4.1-mini"

def generate_reply_with_openai(company_name: str, input_email: str):
    """
    Skilar (subject, body, model_name, llm_latency_ms)
    """
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    prompt = f"""
You are a representative of the company "{company_name}".

You received the following email from a customer:

{input_email}

1) First, infer an appropriate email subject line.
2) Then, write a professional, friendly email reply.

Return your result in JSON with the fields:
- subject
- body
"""

    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=600,
    )
    llm_latency_ms = int((time.time() - t0) * 1000)

    content = resp.choices[0].message.content
    parsed = json.loads(content)

    subject = parsed.get("subject", "").strip()
    body = parsed.get("body", "").strip()
    if not body:
        raise HTTPException(status_code=500, detail="LLM did not return a body")

    return subject, body, MODEL_NAME, llm_latency_ms


def evaluate_with_openai_rubric(company_name: str, scenario: str,
                                input_email: str, generated_body: str):
    """
    LLM-dómari. Skilar (grade_float, latency_ms) 1–10.
    """
    start = time.time()

    prompt = f"""
You are a strict reviewer grading an automatic customer support email reply.

COMPANY:
--------
{company_name}

SCENARIO:
---------
{scenario}

CUSTOMER EMAIL:
---------------
{input_email}

MODEL-GENERATED REPLY:
----------------------
{generated_body}

TASK:
Give a single numeric score from 1 to 10 indicating how good this reply is in terms of:
- correctness and factual accuracy
- helpfulness and clarity
- tone and professionalism
- whether it fully answers the customer’s request/complaint

Respond ONLY with the number, for example: 7.5
"""

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0.0,
    )

    latency_ms = int((time.time() - start) * 1000)
    text = resp.choices[0].message.content.strip()

    m = re.search(r"(\d+(\.\d+)?)", text)
    if not m:
        raise ValueError(f"Could not parse grade from: {text!r}")

    grade = float(m.group(1))
    grade = max(1.0, min(10.0, grade))

    return grade, latency_ms
