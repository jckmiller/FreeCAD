# SPDX-License-Identifier: LGPL-2.1-or-later

import json
import re


def extract_code_block(text):
    pattern = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(text or "")
    if matches:
        return "\n\n".join([m.strip("\n") for m in matches]).strip()
    return (text or "").strip()


def build_messages(user_prompt, active_document_name):
    system_prompt = (
        "You generate only FreeCAD Python scripts. Return Python code suitable for FreeCAD's Python console. "
        "Prefer concise, directly executable code. If explanation is necessary, keep it very short."
    )

    content = (
        "Context:\n"
        "- Active document: {0}\n\n"
        "Task:\n{1}\n\n"
        "Output requirement:\n"
        "- Return Python code in a fenced ```python block when possible."
    ).format(active_document_name, user_prompt)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]


def parse_sse_data_line(line):
    if not line:
        return None, None

    normalized = line.strip()
    if not normalized.startswith("data:"):
        return None, None

    payload = normalized[5:].strip()
    if payload == "[DONE]":
        return "done", None

    try:
        chunk = json.loads(payload)
    except json.JSONDecodeError:
        return None, None

    if "error" in chunk:
        return "error", chunk["error"].get("message", "Unknown API error")

    choices = chunk.get("choices", [])
    if not choices:
        return None, None

    delta = choices[0].get("delta", {})
    return "token", delta.get("content", "")

