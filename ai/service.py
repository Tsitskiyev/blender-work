from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
AI_PLAN_PATH = OUTPUT_DIR / "ai_design_plan.json"
AI_INSTRUCTION_PATH = OUTPUT_DIR / "ai_instruction.md"
AI_SPACE_PROGRAM_PATH = OUTPUT_DIR / "ai_space_program.json"

AIProvider = Literal["openai", "gemini"]
AIGoal = Literal["design_and_gui", "space_program"]

OPENAI_MODELS = ["gpt-5.4-mini", "gpt-5.4", "gpt-5-mini"]
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]


def _normalize_prompt_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _key_candidates(
    provider: AIProvider,
    openai_api_key: str | None,
    gemini_api_key: str | None,
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []

    def push(key: str | None, label: str) -> None:
        resolved = (key or "").strip()
        if not resolved:
            return
        if all(existing_key != resolved for existing_key, _ in candidates):
            candidates.append((resolved, label))

    if provider == "openai":
        push(openai_api_key, "OpenAI API Key field")
        push(os.getenv("OPENAI_API_KEY", ""), "OPENAI_API_KEY")
        return candidates

    push(gemini_api_key, "Gemini API Key field")
    push(os.getenv("GEMINI_API_KEY", ""), "GEMINI_API_KEY")
    push(os.getenv("GOOGLE_API_KEY", ""), "GOOGLE_API_KEY")
    return candidates


def _invalid_key_hint(provider: AIProvider) -> str:
    if provider == "openai":
        return (
            "OpenAI key looks invalid. If you have a valid OPENAI_API_KEY in the environment, "
            "clear the OpenAI API Key field so the app can use it."
        )
    return (
        "Gemini key looks invalid. If you already configured GEMINI_API_KEY or GOOGLE_API_KEY, "
        "clear the Gemini API Key field so the app can use the environment key."
    )


def _is_invalid_key_error(provider: AIProvider, error_text: str) -> bool:
    normalized = error_text.lower()
    shared_markers = ["invalid_api_key", "api_key_invalid", "api key not valid"]
    provider_markers = {
        "openai": ["incorrect api key provided"],
        "gemini": ["please pass a valid api key"],
    }
    return any(marker in normalized for marker in shared_markers + provider_markers[provider])


def _model_candidates(provider: AIProvider, requested_model: str) -> list[str]:
    if provider == "openai":
        return [requested_model]

    fallback_orders = {
        "gemini-2.5-pro": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"],
        "gemini-2.5-flash": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"],
        "gemini-2.5-flash-lite": ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"],
    }
    return fallback_orders.get(requested_model, GEMINI_MODELS.copy())


def _is_resource_exhausted_error(provider: AIProvider, error_text: str) -> bool:
    if provider != "gemini":
        return False

    normalized = error_text.lower()
    markers = [
        "resource_exhausted",
        "quota exceeded",
        "rate limit",
        "rate_limit",
        "too many requests",
    ]
    return any(marker in normalized for marker in markers)


def _resource_exhausted_hint(provider: AIProvider, attempted_models: list[str]) -> str:
    if provider != "gemini":
        return ""

    models = ", ".join(attempted_models)
    return (
        "Gemini quota or rate limit was exhausted"
        + (f" for: {models}." if models else ".")
        + " The app retries lighter Gemini models automatically. "
        "If all retries fail, wait for quota reset or switch provider to OpenAI."
    )


def _is_service_unavailable_error(provider: AIProvider, error_text: str) -> bool:
    if provider != "gemini":
        return False

    normalized = error_text.lower()
    markers = [
        "503",
        "unavailable",
        "service unavailable",
        "currently experiencing high demand",
        "temporarily unavailable",
        "overloaded",
    ]
    return any(marker in normalized for marker in markers)


def _service_unavailable_hint(provider: AIProvider, attempted_models: list[str]) -> str:
    if provider != "gemini":
        return ""

    models = ", ".join(attempted_models)
    suffix = f" Tried: {models}." if models else ""
    return (
        "Gemini is temporarily overloaded or unavailable."
        f"{suffix} The app retries the same model and then falls back to other Gemini models automatically. "
        "If every retry fails, wait a minute and try again or switch provider to OpenAI."
    )


def _summarize_provider_error(provider: AIProvider, error_text: str, attempted_models: list[str]) -> str:
    if _is_invalid_key_error(provider, error_text):
        hint = _invalid_key_hint(provider)
        return "\n".join(part for part in [error_text, hint] if part)

    if _is_resource_exhausted_error(provider, error_text):
        return _resource_exhausted_hint(provider, attempted_models)

    if _is_service_unavailable_error(provider, error_text):
        return _service_unavailable_hint(provider, attempted_models)

    return error_text


def _load_schema_types() -> tuple[type[Any], type[Any]]:
    try:
        from ai.schema import GUIParameterPlan, HousePlanResponse
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependency"
        if missing == "pydantic":
            raise RuntimeError(
                "The AI feature requires the 'pydantic' package. "
                "Install requirements into the current interpreter first."
            ) from exc
        raise
    return GUIParameterPlan, HousePlanResponse


def _load_validation_error_type() -> type[Exception]:
    try:
        from pydantic import ValidationError
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The AI feature requires the 'pydantic' package. "
            "Install requirements into the current interpreter first."
        ) from exc
    return ValidationError


@dataclass(slots=True)
class AIInterpretationResult:
    success: bool = False
    message: str = ""
    parsed: dict[str, Any] | None = None
    gui_parameters: dict[str, Any] = field(default_factory=dict)
    technical_instruction: str = ""
    plan_path: str = ""
    instruction_path: str = ""
    space_program_path: str = ""
    request_id: str = ""
    provider: str = ""
    model: str = ""


def _build_system_prompt(goal: AIGoal) -> str:
    base = (
        "You are a senior residential architect and Blender planning assistant. "
        "You transform a user's house brief into structured design data for a desktop Blender generator.\n\n"
        "Global rules:\n"
        "- STRICT PROMPT MODE: the user's brief is the only design source of truth.\n"
        "- Never preserve or reuse previous GUI state unless the user explicitly repeats it in the brief.\n"
        "- Never use a repeated template house.\n"
        "- Style must come from the user brief, not from your own preferences.\n"
        "- Only output values supported by the GUI schema.\n"
        "- Do not invent unsupported controls.\n"
        "- Do not add columns, pediments, porticos, garages, terraces, balconies, fences, pools, towers or any other feature unless the brief explicitly asks for them.\n"
        "- Treat explicit user requirements as hard constraints.\n"
        "- If symmetry is requested, keep the composition axial, centered and mirrored unless the prompt explicitly asks for asymmetry.\n"
        "- If dimensions are missing, infer only the minimum needed to produce a coherent house. Do not add decorative or stylistic extras beyond the brief.\n"
        "- If the user writes in Russian, produce the instruction in Russian.\n"
        "- If a modern concept is requested, do not force classical elements unless asked.\n"
        "- If the brief is silent about an optional feature, prefer False rather than inventing it.\n"
    )
    if goal == "space_program":
        return (
            base
            + "Primary goal: prioritize room program quality, adjacency logic, circulation, "
            "and a parser-ready space-planning description while still producing valid GUI parameters."
        )
    return (
        base
        + "Primary goal: produce a strong design concept, valid GUI parameters, "
        "a room program, and a detailed Blender-oriented technical instruction."
    )


def _build_user_prompt(user_brief: str, current_params: dict[str, Any], goal: AIGoal) -> str:
    goal_text = (
        "Focus heavily on internal planning, room adjacency, zoning, and parser-ready room structure."
        if goal == "space_program"
        else "Focus on a balanced output: unique style, room program, generator parameters, and technical instruction."
    )
    supported_controls = ", ".join(sorted(current_params.keys()))
    return (
        "User brief for AI interpretation:\n"
        f"{user_brief.strip()}\n\n"
        "Supported GUI controls in the desktop app:\n"
        f"{supported_controls}\n\n"
        "Important: ignore previous GUI state. The brief above overrides everything. "
        "Do not keep old options just because they were used before.\n\n"
        f"Goal mode: {goal}\n"
        f"{goal_text}\n\n"
        "Produce:\n"
        "- a unique architectural concept\n"
        "- valid GUI parameters for the generator\n"
        "- a complete space program with room sizing, openings, adjacency and future parser notes\n"
        "- a detailed technical instruction as markdown\n"
    )


def _sanitize_gui_parameters(raw: Any) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    sanitized = raw.model_dump()

    def clamp(name: str, low: float, high: float) -> None:
        original = float(sanitized[name])
        updated = max(low, min(original, high))
        if updated != original:
            warnings.append(f"{name} adjusted from {original} to {updated}.")
            sanitized[name] = updated

    clamp("width", 6.0, 60.0)
    clamp("depth", 6.0, 45.0)
    clamp("floor_height", 2.6, 4.8)
    sanitized["floors"] = max(1, min(int(sanitized["floors"]), 5))
    sanitized["window_count_front"] = max(0, min(int(sanitized["window_count_front"]), 9))
    if sanitized["roof_type"] == "flat":
        sanitized["roof_pitch"] = 0.0
    else:
        clamp("roof_pitch", 10.0, 55.0)

    if sanitized["floors"] < 2 and sanitized["has_balcony"]:
        sanitized["has_balcony"] = False
        warnings.append("has_balcony disabled because floors < 2.")

    if sanitized["floors"] == 1 and sanitized["window_count_front"] % 2 == 1:
        sanitized["window_count_front"] += 1
        warnings.append("window_count_front increased by 1 to keep a valid single-floor centered facade.")

    return sanitized, warnings


def _apply_prompt_hard_guards(user_brief: str, sanitized: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    text = _normalize_prompt_text(user_brief)

    feature_terms = {
        "has_columns": {
            "positive": ("column", "columns", "колон", "colonnade"),
            "negative": ("no column", "no columns", "without column", "without columns", "без колон", "убрать колон", "remove column"),
        },
        "has_pediment": {
            "positive": ("pediment", "фронтон"),
            "negative": ("no pediment", "without pediment", "без фронтон", "убрать фронтон", "remove pediment"),
        },
        "has_portico": {
            "positive": ("portico", "портик"),
            "negative": ("no portico", "without portico", "без портик", "убрать портик", "remove portico"),
        },
        "has_garage": {
            "positive": ("garage", "carport", "parking bay", " гараж", "гараж", "навес для машины", "парковк"),
            "negative": ("no garage", "without garage", "remove garage", "без гараж", "убрать гараж"),
        },
        "has_terrace": {
            "positive": ("terrace", "deck terrace", "roof deck", "rear deck", "veranda", "porch deck", "террас", "веранд"),
            "negative": ("no terrace", "without terrace", "remove terrace", "без террас", "убрать террас"),
        },
        "has_balcony": {
            "positive": ("balcony", "loggia", "балкон", "лодж"),
            "negative": ("no balcony", "without balcony", "remove balcony", "без балкон", "убрать балкон"),
        },
        "has_fence": {
            "positive": ("fence", "gate fence", "забор", "ограждение участка"),
            "negative": ("no fence", "without fence", "remove fence", "без забор", "убрать забор"),
        },
    }

    for key, terms in feature_terms.items():
        if _contains_any(text, terms["negative"]):
            if sanitized.get(key) is not False:
                warnings.append(f"{key} forced to False from prompt.")
            sanitized[key] = False
        elif _contains_any(text, terms["positive"]):
            if sanitized.get(key) is not True:
                warnings.append(f"{key} forced to True from prompt.")
            sanitized[key] = True
        else:
            if sanitized.get(key):
                warnings.append(f"{key} cleared because it was not explicitly requested in the prompt.")
            sanitized[key] = False

    if _contains_any(text, ("flat roof", "плоская крыша", "плоскую крыш", "эксплуатируемая кровля")):
        sanitized["roof_type"] = "flat"
        sanitized["roof_pitch"] = 0.0
    elif _contains_any(text, ("hip roof", "вальмов", "четырехскат")):
        sanitized["roof_type"] = "hip"
    elif _contains_any(text, ("gable roof", "двускат", "щипцов")):
        sanitized["roof_type"] = "gable"

    if _contains_any(text, ("log cabin", "log house", "rustic cabin", "timber house", "stacked round logs", "round logs", "сруб", "бревенчат", "бревно")):
        sanitized["wall_material"] = "log_wood"
    elif _contains_any(text, ("brick facade", "brick wall", "brick house", "brick exterior", "brickwork", "кирпичный фасад", "кирпичный дом", "из кирпич")):
        sanitized["wall_material"] = "brick"
    elif _contains_any(text, ("stone", "slate", "камень", "сланец")):
        sanitized["wall_material"] = "stone"
    elif _contains_any(text, ("concrete", "бетон")):
        sanitized["wall_material"] = "concrete"
    elif _contains_any(text, ("stucco", "plaster", "штукатур")):
        sanitized["wall_material"] = "stucco"

    if _contains_any(text, ("symmetr", "симметр")):
        current_count = int(sanitized.get("window_count_front", 0))
        if current_count == 1:
            sanitized["window_count_front"] = 3
            warnings.append("window_count_front adjusted for a centered symmetric facade.")
        elif current_count > 0 and current_count % 2 == 0 and int(sanitized.get("floors", 1)) >= 2:
            sanitized["window_count_front"] = current_count + 1
            warnings.append("window_count_front adjusted to keep upper-floor center axis symmetry.")

    if _contains_any(text, ("barnhouse", "modern barnhouse", "scandinavian", "scandi", "minimal barn")):
        if sanitized.get("arch_style") != "scandinavian_barnhouse":
            warnings.append("arch_style forced to scandinavian_barnhouse from prompt.")
        sanitized["arch_style"] = "scandinavian_barnhouse"
        if sanitized.get("roof_type") != "gable":
            warnings.append("roof_type forced to gable for barnhouse prompt.")
        sanitized["roof_type"] = "gable"
        if float(sanitized.get("roof_pitch", 0.0)) < 24.0:
            sanitized["roof_pitch"] = 30.0

    if _contains_any(text, ("log cabin", "log house", "rustic cabin", "timber house", "stacked round logs", "round logs", "сруб", "бревенчат")):
        if sanitized.get("arch_style") != "rustic_log_cabin":
            warnings.append("arch_style forced to rustic_log_cabin from prompt.")
        sanitized["arch_style"] = "rustic_log_cabin"
        sanitized["roof_type"] = "gable"
        sanitized["roof_pitch"] = max(28.0, float(sanitized.get("roof_pitch", 0.0)))

    if _contains_any(text, ("wood cladding", "timber cladding", "planken", "charred wood", "burnt wood")) and _contains_any(text, ("stucco", "plaster", "render")):
        sanitized["wall_material"] = "stucco"

    sanitized["special_notes"] = user_brief.strip()
    return sanitized, warnings


def _save_ai_outputs(parsed: dict[str, Any], instruction: str) -> tuple[str, str, str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AI_PLAN_PATH.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    AI_INSTRUCTION_PATH.write_text(instruction, encoding="utf-8")
    AI_SPACE_PROGRAM_PATH.write_text(
        json.dumps(parsed.get("space_program", {}), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(AI_PLAN_PATH), str(AI_INSTRUCTION_PATH), str(AI_SPACE_PROGRAM_PATH)


def _call_openai(
    api_key: str,
    model: str,
    user_brief: str,
    current_params: dict[str, Any],
    goal: AIGoal,
) -> tuple[HousePlanResponse, str]:
    from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

    _, house_plan_response = _load_schema_types()

    client = OpenAI(api_key=api_key, timeout=90.0)
    try:
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": _build_system_prompt(goal)},
                {"role": "user", "content": _build_user_prompt(user_brief, current_params, goal)},
            ],
            text_format=house_plan_response,
        )
    except APITimeoutError as exc:
        raise RuntimeError("OpenAI request timed out.") from exc
    except APIConnectionError as exc:
        raise RuntimeError(f"OpenAI connection error: {exc}") from exc
    except APIStatusError as exc:
        request_id = getattr(exc, "request_id", "") or ""
        suffix = f" Request ID: {request_id}" if request_id else ""
        raise RuntimeError(f"OpenAI API returned status {exc.status_code}.{suffix}") from exc

    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed structured output.")
    return parsed, getattr(response, "_request_id", "") or ""


def _call_gemini(
    api_key: str,
    model: str,
    user_brief: str,
    current_params: dict[str, Any],
    goal: AIGoal,
) -> tuple[HousePlanResponse, str]:
    from google import genai
    from google.genai import types

    _, house_plan_response = _load_schema_types()

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=_build_user_prompt(user_brief, current_params, goal),
            config=types.GenerateContentConfig(
                system_instruction=_build_system_prompt(goal),
                response_mime_type="application/json",
                response_schema=house_plan_response,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    parsed = getattr(response, "parsed", None)
    if parsed is None:
        raise RuntimeError("Gemini returned no parsed structured output.")
    return parsed, ""


def _retry_attempt_count(provider: AIProvider, error_text: str) -> int:
    if _is_service_unavailable_error(provider, error_text):
        return 3
    return 1


def _retry_delay_seconds(provider: AIProvider, error_text: str, attempt_index: int) -> float:
    if _is_service_unavailable_error(provider, error_text):
        return [1.2, 2.4, 4.0][min(attempt_index, 2)]
    return 0.0


def generate_house_plan(
    user_brief: str,
    current_params: dict[str, Any],
    *,
    provider: AIProvider = "openai",
    goal: AIGoal = "design_and_gui",
    model: str | None = None,
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> AIInterpretationResult:
    result = AIInterpretationResult(provider=provider)
    validation_error_type = Exception

    if not user_brief.strip():
        result.message = "AI brief is empty."
        return result

    model_pool = OPENAI_MODELS if provider == "openai" else GEMINI_MODELS
    resolved_model = model if model in model_pool else model_pool[0]
    result.model = resolved_model

    key_candidates = _key_candidates(provider, openai_api_key, gemini_api_key)
    if not key_candidates:
        if provider == "openai":
            result.message = "OpenAI API key is missing. Paste a key in the AI section or set OPENAI_API_KEY."
        else:
            result.message = "Gemini API key is missing. Paste a key in the AI section or set GEMINI_API_KEY."
        return result

    parsed = None
    request_id = ""
    used_key_label = ""
    used_model = resolved_model
    fallback_note = ""
    last_error = ""
    attempted_models: list[str] = []

    try:
        validation_error_type = _load_validation_error_type()
    except validation_error_type as exc:
        result.message = f"AI response validation failed: {exc}"
        return result
    except Exception as exc:
        result.message = str(exc)
        return result

    for key_index, (resolved_key, key_label) in enumerate(key_candidates):
        candidate_models = _model_candidates(provider, resolved_model)
        for model_index, candidate_model in enumerate(candidate_models):
            if candidate_model not in attempted_models:
                attempted_models.append(candidate_model)
            attempt_index = 0
            retry_attempts = 1
            while attempt_index < retry_attempts:
                try:
                    if provider == "openai":
                        parsed, request_id = _call_openai(
                            resolved_key,
                            candidate_model,
                            user_brief,
                            current_params,
                            goal,
                        )
                    else:
                        parsed, request_id = _call_gemini(
                            resolved_key,
                            candidate_model,
                            user_brief,
                            current_params,
                            goal,
                        )
                    used_key_label = key_label
                    used_model = candidate_model
                    note_parts: list[str] = []
                    if key_index > 0:
                        note_parts.append(
                            f"Primary key source failed, fallback succeeded with {key_label}."
                        )
                    if model_index > 0 or candidate_model != resolved_model:
                        note_parts.append(
                            f"Requested model {resolved_model} was unavailable, fallback succeeded with {candidate_model}."
                        )
                    if attempt_index > 0:
                        note_parts.append(
                            f"Temporary provider error recovered after retry {attempt_index + 1} on {candidate_model}."
                        )
                    fallback_note = "\n".join(note_parts)
                    break
                except validation_error_type as exc:
                    result.message = f"AI response validation failed: {exc}"
                    return result
                except Exception as exc:
                    last_error = str(exc)
                    retry_attempts = _retry_attempt_count(provider, last_error)
                    if _is_invalid_key_error(provider, last_error):
                        break
                    if attempt_index < retry_attempts - 1:
                        time.sleep(_retry_delay_seconds(provider, last_error, attempt_index))
                        attempt_index += 1
                        continue
                    if model_index < len(candidate_models) - 1 and (
                        _is_resource_exhausted_error(provider, last_error)
                        or _is_service_unavailable_error(provider, last_error)
                    ):
                        break
                    if key_index < len(key_candidates) - 1 and _is_invalid_key_error(provider, last_error):
                        continue
                    result.message = _summarize_provider_error(provider, last_error, attempted_models)
                    return result
                attempt_index += 1
            if parsed is not None:
                break
        if parsed is not None:
            break
        if last_error and not _is_invalid_key_error(provider, last_error):
            result.message = _summarize_provider_error(provider, last_error, attempted_models)
            return result

    if parsed is None:
        result.message = _summarize_provider_error(provider, last_error or "AI request failed.", attempted_models)
        return result

    gui_parameters, warnings = _sanitize_gui_parameters(parsed.gui_parameters)
    gui_parameters, prompt_warnings = _apply_prompt_hard_guards(user_brief, gui_parameters)
    parsed_payload = parsed.model_dump()
    parsed_payload["gui_parameters"] = gui_parameters
    all_warnings = warnings + prompt_warnings
    if all_warnings:
        parsed_payload["constraint_notes"] = parsed_payload.get("constraint_notes", []) + all_warnings

    instruction = parsed.technical_instruction_markdown
    plan_path, instruction_path, space_program_path = _save_ai_outputs(parsed_payload, instruction)

    result.success = True
    result.parsed = parsed_payload
    result.gui_parameters = gui_parameters
    result.technical_instruction = instruction
    result.plan_path = plan_path
    result.instruction_path = instruction_path
    result.space_program_path = space_program_path
    result.request_id = request_id
    result.message = (
        "AI design brief generated successfully.\n"
        f"Provider: {provider}\n"
        f"Model: {used_model}\n"
        f"Key source: {used_key_label}\n"
        f"Plan: {Path(plan_path).name}\n"
        f"Space program: {Path(space_program_path).name}\n"
        f"Instruction: {Path(instruction_path).name}"
    )
    if fallback_note:
        result.message = f"{result.message}\n{fallback_note}"
    return result
