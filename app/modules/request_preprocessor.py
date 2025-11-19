import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI

from app.helpers.openai_helper import ChatRequest, Message, openai_helper
from app.main import app as fastapi_app

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an intelligent API router that maps natural language requests to FastAPI endpoints. "
    "Always respond with valid JSON only. Never include explanations outside of the JSON."
)

DEFAULT_RESULT: Dict[str, Any] = {
    "selected_api": None,
    "confidence": 0.0,
    "reasoning": "",
    "parameters": {},
}


def _get_openapi_schema(api_app: FastAPI) -> Dict[str, Any]:
    try:
        return api_app.openapi()
    except Exception as exc:
        logger.exception("Failed to load OpenAPI schema: %s", exc)
        raise


def _extract_api_entries(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    paths = schema.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            summary = details.get("summary") or details.get("operationId") or "No summary provided"
            description = details.get("description", "")
            tags = details.get("tags", [])
            parameters = details.get("parameters", [])
            request_body = details.get("requestBody", {})
            required_params = [param["name"] for param in parameters if param.get("required")]
            optional_params = [param["name"] for param in parameters if not param.get("required")]
            body_types = list(request_body.get("content", {}).keys())

            entries.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "tags": tags,
                    "required_params": required_params,
                    "optional_params": optional_params,
                    "body_types": body_types,
                }
            )
    return entries


def _format_api_catalog(entries: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for idx, entry in enumerate(entries, 1):
        lines.append(f"{idx}. {entry['method']} {entry['path']}")
        lines.append(f"   summary: {entry['summary']}")
        if entry["description"]:
            lines.append(f"   description: {entry['description']}")
        if entry["tags"]:
            lines.append(f"   tags: {', '.join(entry['tags'])}")
        if entry["required_params"]:
            lines.append(f"   required_params: {', '.join(entry['required_params'])}")
        if entry["optional_params"]:
            lines.append(f"   optional_params: {', '.join(entry['optional_params'])}")
        if entry["body_types"]:
            lines.append(f"   body_content_types: {', '.join(entry['body_types'])}")
    return "\n".join(lines)


def _build_user_message(user_prompt: str, catalog: str) -> str:
    return (
        f"User request:\n{user_prompt}\n\n"
        "Available APIs:\n"
        f"{catalog}\n\n"
        "Respond with JSON using the following structure:\n"
        "{\n"
        '  "selected_api": {\n'
        '    "method": "HTTP_VERB or null",\n'
        '    "path": "/api/path or null"\n'
        "  },\n"
        '  "confidence": a number between 0 and 1,\n'
        '  "reasoning": "Short explanation",\n'
        '  "parameters": {\n'
        '    "param_name": "value or placeholder"\n'
        "  }\n"
        "}\n"
        "If no API fits, set selected_api to null and explain why."
    )


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(text[start : end + 1])
        raise


def _normalize_result(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    result = DEFAULT_RESULT.copy()
    if not isinstance(raw, dict):
        return result

    selected_api = raw.get("selected_api")
    if isinstance(selected_api, dict):
        method = selected_api.get("method")
        path = selected_api.get("path")
        if isinstance(method, str) and isinstance(path, str):
            result["selected_api"] = {"method": method.upper(), "path": path}
        else:
            result["selected_api"] = None

    confidence = raw.get("confidence")
    if isinstance(confidence, (int, float)):
        result["confidence"] = max(0.0, min(float(confidence), 1.0))

    reasoning = raw.get("reasoning")
    if isinstance(reasoning, str):
        result["reasoning"] = reasoning.strip()

    params = raw.get("parameters")
    if isinstance(params, dict):
        result["parameters"] = {str(k): str(v) for k, v in params.items()}

    return result


async def suggest_api_for_prompt(
    user_prompt: str,
    api_app: FastAPI = fastapi_app,
    model: Optional[str] = "gpt-4o",
) -> Dict[str, Any]:
    """
    Analyze a user prompt and suggest the most appropriate API endpoint.

    Args:
        user_prompt: Natural language request from the user.
        api_app: FastAPI application to derive the OpenAPI schema from.
        model: OpenAI model identifier (defaults to gpt-4o).

    Returns:
        Normalized JSON-friendly dictionary describing the chosen API.
    """
    schema = _get_openapi_schema(api_app)
    entries = _extract_api_entries(schema)
    if not entries:
        logger.warning("No API entries found in schema.")
        return DEFAULT_RESULT.copy()

    catalog = _format_api_catalog(entries)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=_build_user_message(user_prompt, catalog)),
    ]

    request = ChatRequest(messages=messages, model=model, temperature=0.0, max_tokens=400)
    try:
        response = await openai_helper.chat_completion(request)
        raw_data = _extract_json(response.content)
    except Exception as exc:
        logger.exception("Failed to obtain API suggestion: %s", exc)
        return DEFAULT_RESULT.copy()

    return _normalize_result(raw_data)

