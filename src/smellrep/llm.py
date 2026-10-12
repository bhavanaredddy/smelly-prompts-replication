"""Minimal client for a local Ollama server (free, no API key)."""

import json
import os
import re
import time

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("SMELLREP_MODEL", "llama3.2:3b")


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    json_mode: bool = True,
    temperature: float = 0.0,
    seed: int = 42,
    num_ctx: int = 8192,
    num_predict: int = 4096,
    timeout: int = 1800,
) -> tuple[str, dict]:
    """Returns (content, stats). Stats include token counts and wall time."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    if json_mode:
        payload["format"] = "json"
    t0 = time.time()
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    stats = {
        "seconds": round(time.time() - t0, 1),
        "prompt_tokens": body.get("prompt_eval_count"),
        "output_tokens": body.get("eval_count"),
        "done_reason": body.get("done_reason"),
    }
    return body["message"]["content"], stats


def parse_json(text: str):
    """Parses model output, tolerating code fences and trailing prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start >= 0:
        for end in range(len(text), start, -1):
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON found in model output")


def find_list(obj, preferred_keys: tuple[str, ...]):
    """Small models sometimes wrap or rename the top-level list; find it anyway."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in preferred_keys:
            if isinstance(obj.get(k), list):
                return obj[k]
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        if obj and all(isinstance(v, dict) for v in obj.values()):
            return [{"requirement_id": k, **v} for k, v in obj.items()]
    return []


def available(model: str = DEFAULT_MODEL) -> bool:
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
    except requests.RequestException:
        return False
    return any(t["name"] == model or t["name"].split(":")[0] == model for t in tags.get("models", []))
