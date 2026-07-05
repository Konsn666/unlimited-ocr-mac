"""Translation via any OpenAI-compatible API (configurable)."""
import json
import re
import urllib.request
import urllib.error
from config import TRANSLATE_API_BASE, TRANSLATE_API_KEY, TRANSLATE_MODEL


LANG_NAMES = {
    "zh-CN": "简体中文", "zh-TW": "繁體中文", "en": "English",
    "ja": "日本語", "ko": "한국어", "fr": "Français",
    "de": "Deutsch", "es": "Español", "pt": "Português",
    "ru": "Русский", "ar": "العربية", "th": "ไทย",
    "vi": "Tiếng Việt", "id": "Bahasa Indonesia",
}

# Max items per batch to avoid token limit issues
BATCH_SIZE = 30


def translate_page(detections: list[dict], source_lang: str = "auto", target_lang: str = "zh-CN") -> list[dict]:
    """Translate text detections using any OpenAI-compatible API.

    Splits items into batches of BATCH_SIZE to avoid max_tokens truncation.
    Returns list of {"index": int, "original": str, "translated": str}
    """
    if not TRANSLATE_API_BASE or not TRANSLATE_API_KEY:
        raise ValueError("Translation API not configured. Set TRANSLATE_API_BASE and TRANSLATE_API_KEY in .env")

    # Collect translatable items
    items = []
    for i, det in enumerate(detections):
        if det.get("type") in ("text", "title", "table"):
            items.append({"index": i, "type": det["type"], "text": det["text"]})

    if not items:
        return []

    # Translate in batches and merge results
    all_results = []
    for batch_start in range(0, len(items), BATCH_SIZE):
        batch = items[batch_start:batch_start + BATCH_SIZE]
        batch_results = _translate_batch(batch, source_lang, target_lang)
        all_results.extend(batch_results)

    return all_results


def _translate_batch(items: list[dict], source_lang: str, target_lang: str) -> list[dict]:
    """Translate a single batch of items."""
    tgt_label = LANG_NAMES.get(target_lang, target_lang)
    src_label = LANG_NAMES.get(source_lang, source_lang) if source_lang != "auto" else "auto-detect"

    text_blocks = "\n".join(f'{it["index"]}: {it["text"]}' for it in items)

    system_msg = (
        f"You are a professional translator. Translate to {tgt_label}. "
        f"Source language: {src_label}. "
        f"Output ONLY valid JSON: {{\"translations\": [{{\"index\": 0, \"translated\": \"...\"}}]}}. "
        f"You MUST translate ALL {len(items)} items. Do not skip any. "
        f"IMPORTANT: In the translated field, output ONLY the translated text. "
        f"Do NOT include any labels, tags, prefixes like [title] or [text]."
    )
    user_msg = f"Text blocks ({len(items)} items):\n{text_blocks}"

    # Call OpenAI-compatible chat completions API
    url = f"{TRANSLATE_API_BASE.rstrip('/')}/chat/completions"
    body = json.dumps({
        "model": TRANSLATE_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 16384,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TRANSLATE_API_KEY}",
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise ValueError(f"Translation API error {e.code}: {err_body[:500]}")
    except Exception as e:
        raise ValueError(f"Translation API failed: {e}")

    # Extract content from response
    resp_text = ""
    try:
        resp_text = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise ValueError(f"Unexpected API response format: {json.dumps(result)[:300]}")

    # Try to extract JSON from possible markdown code fences
    if "```" in resp_text:
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", resp_text, re.DOTALL)
        if m:
            resp_text = m.group(1).strip()

    # Try to parse JSON, with repair for truncated responses
    try:
        data = json.loads(resp_text)
        translations = data.get("translations", [])
    except json.JSONDecodeError:
        # Attempt to repair truncated JSON by closing open brackets
        translations = _try_repair_json(resp_text)

    trans_map = {t["index"]: _clean_translation(t["translated"]) for t in translations if "index" in t and "translated" in t}

    return [
        {"index": it["index"], "original": it["text"], "translated": trans_map.get(it["index"], it["text"])}
        for it in items
    ]


def _clean_translation(text: str) -> str:
    """Remove any [title], [text], [table] prefixes that LLM may include."""
    return re.sub(r'^\[(?:title|text|table)\]\s*', '', text)


def _try_repair_json(text: str) -> list[dict]:
    """Attempt to extract partial translations from truncated JSON.

    When the LLM output is cut off by max_tokens, we may get something like:
      {"translations": [{"index": 0, "translated": "foo"}, {"index": 1, "transla
    We try to recover completed entries by finding all fully-formed objects.
    """
    # Find all completed {"index": N, "translated": "..."} objects
    pattern = re.compile(r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"translated"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}')
    matches = pattern.findall(text)
    if matches:
        return [{"index": int(m[0]), "translated": m[1].replace('\\"', '"').replace("\\n", "\n")} for m in matches]

    # If we can't recover anything, raise the original error
    raise ValueError(f"Translation returned non-JSON: {text[:300]}")
