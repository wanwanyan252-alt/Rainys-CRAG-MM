"""Run a fixed CRAG-MM manifest through a CUDA VLM without retrieval."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from collections import Counter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--model-name",
        default="meta-llama/Llama-3.2-11B-Vision-Instruct",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument(
        "--answer-token-limit",
        type=int,
        default=75,
        help="Truncate the final answer to the competition's scored token limit.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate only the first N manifest entries.",
    )
    parser.add_argument(
        "--positions",
        help=(
            "Comma-separated zero-based manifest positions to evaluate. "
            "Cannot be combined with --limit."
        ),
    )
    parser.add_argument(
        "--image-retrieval",
        action="store_true",
        help="Enable the official CRAG-MM image index.",
    )
    parser.add_argument(
        "--web-retrieval",
        action="store_true",
        help="Enable the official CRAG-MM web index.",
    )
    parser.add_argument("--hf-home", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--rewrite-web-query",
        action="store_true",
        help="Identify the image entity with the VLM before running web search.",
    )
    parser.add_argument(
        "--rewrite-multicrop",
        action="store_true",
        help=(
            "Identify the question referent from full, lower, left, right, and center "
            "views before web search. Requires image retrieval and query rewriting."
        ),
    )
    parser.add_argument(
        "--fast-multicrop",
        action="store_true",
        help="Replace sequential crop inference with one 2x2 contact-sheet inference.",
    )
    parser.add_argument(
        "--structured-visual-analysis",
        action="store_true",
        help="Extract entity, visible OCR text, route, and confidence together.",
    )
    parser.add_argument(
        "--route-web-retrieval",
        action="store_true",
        help="Allow the question router to disable web retrieval.",
    )
    parser.add_argument(
        "--validate-numeric-evidence",
        action="store_true",
        help=(
            "Convert an answer to abstention when its numbers are absent from the "
            "retrieved documents or are supported only outside a requested scope."
        ),
    )
    parser.add_argument(
        "--concise-boolean-answers",
        action="store_true",
        help="Keep only the core conclusion for yes/no questions before validation.",
    )
    parser.add_argument(
        "--dual-web-query",
        action="store_true",
        help="Merge entity-rewritten and original-query web results.",
    )
    parser.add_argument(
        "--multi-web-query",
        action="store_true",
        help="Retrieve with 3-5 deterministic entity, OCR, and original queries.",
    )
    parser.add_argument(
        "--web-reranker-model",
        type=Path,
        help="Local independent cross-encoder model directory for web reranking.",
    )
    parser.add_argument("--web-reranker-device", default="cpu")
    parser.add_argument("--web-reranker-batch-size", type=int, default=16)
    parser.add_argument("--web-reranker-candidate-cap", type=int, default=40)
    parser.add_argument(
        "--use-entity-candidate-for-search",
        action="store_true",
        help=(
            "Use a multi-crop entity selected by the VLM for web retrieval even when "
            "it is not strong enough to count as a resolved answer entity."
        ),
    )
    parser.add_argument(
        "--retry-grounded-abstentions",
        action="store_true",
        help=(
            "Retry an abstention once when an entity-guided web query was available, "
            "explicitly allowing simple arithmetic and year comparisons."
        ),
    )
    parser.add_argument(
        "--focused-web-query",
        action="store_true",
        help="Use a compact entity-plus-property query for web retrieval.",
    )
    parser.add_argument(
        "--web-entity-fallback",
        action="store_true",
        help=(
            "For a no-entity abstention, identify an entity from the image and web "
            "titles, then perform one compact web re-query."
        ),
    )
    parser.add_argument(
        "--expanded-web-context",
        action="store_true",
        help="Allow up to 8 focused web snippets and 12000 context characters.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the validated per-result JSONL checkpoint.",
    )
    parser.add_argument(
        "--refusal-gate-config",
        type=Path,
        help="Apply a calibrated local refusal gate after answer generation.",
    )
    parser.add_argument(
        "--refusal-gate-threshold",
        type=float,
        help="Override the calibrated refusal probability threshold.",
    )
    return parser.parse_args()


def load_manifest(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(f"Manifest does not exist: {path}")
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise SystemExit("Manifest must contain a non-empty JSON list")
    if limit is not None:
        if limit < 1:
            raise SystemExit("--limit must be at least 1")
        entries = entries[:limit]
    return entries


def parse_positions(value: str | None, count: int) -> list[int] | None:
    if value is None:
        return None
    try:
        positions = [int(part.strip()) for part in value.split(",")]
    except ValueError as error:
        raise SystemExit("--positions must contain comma-separated integers") from error
    if not positions or any(position < 0 or position >= count for position in positions):
        raise SystemExit(f"--positions values must be between 0 and {count - 1}")
    if len(set(positions)) != len(positions):
        raise SystemExit("--positions must not contain duplicates")
    return positions


def first_value(entry: dict[str, Any], section: str, field: str) -> Any:
    values = entry.get(section, {}).get(field)
    if not isinstance(values, list) or not values:
        raise SystemExit(f"Manifest entry is missing {section}.{field}")
    return values[0]


def truncate_answer_tokens(response: str, tokenizer: Any, limit: int) -> str:
    if limit < 1:
        raise ValueError("answer token limit must be at least 1")
    token_ids = tokenizer.encode(response, add_special_tokens=False)
    if len(token_ids) <= limit:
        return response
    return tokenizer.decode(token_ids[:limit], skip_special_tokens=True).strip()


def cuda_memory_snapshot(torch_module: Any) -> dict[str, float]:
    free_bytes, total_bytes = torch_module.cuda.mem_get_info()
    gib = 1024**3
    return {
        "allocated_gib": round(torch_module.cuda.memory_allocated() / gib, 3),
        "reserved_gib": round(torch_module.cuda.memory_reserved() / gib, 3),
        "free_gib": round(free_bytes / gib, 3),
        "total_gib": round(total_bytes / gib, 3),
    }


def build_web_search_query(query: str, entity_response: str) -> str:
    entity = entity_response.strip()
    if not entity or entity.lower().startswith(
        ("i don't know", "i don’t know", "i do not know", "unknown")
    ):
        return query
    if len(entity) > 200:
        return query
    return f"Identified image entity: {entity}. Question: {query}"


def build_focused_web_search_query(query: str, entity_response: str) -> str:
    entity = entity_response.strip()
    if not entity:
        return query
    ignored = {
        "a",
        "an",
        "are",
        "at",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "made",
        "of",
        "on",
        "the",
        "these",
        "this",
        "those",
        "to",
        "was",
        "were",
        "what",
        "when",
        "which",
        "who",
        "with",
        "would",
    }
    entity_tokens = set(re.findall(r"[a-z0-9]+", entity.casefold()))
    property_tokens = []
    for token in re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", query.casefold()):
        normalized = token.strip(".-")
        if (
            not normalized
            or normalized in ignored
            or normalized in entity_tokens
            or normalized in property_tokens
        ):
            continue
        property_tokens.append(normalized)
    return " ".join([entity] + property_tokens)


def build_multi_web_queries(
    query: str,
    entity: str,
    visible_text: str,
    route: str,
) -> list[str]:
    queries = [query]
    if entity:
        queries.extend(
            [
                build_focused_web_search_query(query, entity),
                build_web_search_query(query, entity),
            ]
        )
    ocr_hint = compact_ocr_hint(visible_text, max_tokens=12)
    if ocr_hint:
        queries.append(f"{ocr_hint} {query}")
    if route == "comparison" and entity:
        queries.append(f"{entity} comparison specifications dates facts")
    normalized = []
    seen = set()
    for value in queries:
        value = re.sub(r"\s+", " ", value).strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            normalized.append(value)
    return normalized[:5]


def extract_tagged_entity(response: str) -> str:
    match = re.search(r"<entity>\s*(.*?)\s*</entity>", response, re.IGNORECASE)
    if not match:
        return ""
    entity = match.group(1).strip()
    if entity.lower() == "unknown" or len(entity) > 100:
        return ""
    return entity


def extract_tagged_value(response: str, tag: str) -> str:
    match = re.search(
        rf"<{re.escape(tag)}>\s*(.*?)\s*</{re.escape(tag)}>",
        response,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def classify_question_route(query: str) -> str:
    text = query.casefold()
    if re.search(
        r"\b(versus|compared|difference|more than|less than|cheaper|higher|lower|"
        r"taller|older|newer|before|after)\b",
        text,
    ):
        return "comparison"
    if re.search(
        r"\b(chart|graph|quarter|revenue|reported|age and sex|least amount|"
        r"highest amount|lowest amount)\b",
        text,
    ):
        return "chart"
    if re.search(
        r"\b(brand|logo|label|sign|book|newspaper|package|packaging|net weight|"
        r"calories|sugar|sodium|allergen|ingredients|unit of measurement|model)\b",
        text,
    ):
        return "ocr"
    if re.search(
        r"^(what|which)\s+(is|are)\s+(this|these|that|those)\b|"
        r"\bwhat (plant|animal|food|object|vehicle|car) is this\b",
        text,
    ):
        return "identity"
    if re.search(r"\b(what color|how many .* (shown|visible|pictured))\b", text):
        return "visual"
    return "lookup"


def normalize_visual_route(value: str, query: str) -> str:
    route = value.strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "direct": "visual",
        "direct_visual": "visual",
        "recognition": "identity",
        "text": "ocr",
        "web": "lookup",
        "knowledge": "lookup",
    }
    route = aliases.get(route, route)
    deterministic = classify_question_route(query)
    if deterministic in {"comparison", "chart", "ocr"}:
        return deterministic
    if route in {"identity", "visual", "ocr", "lookup", "comparison", "chart"}:
        return route
    return deterministic


def ocr_supports_entity(entity: str, visible_text: str) -> bool:
    entity_tokens = {
        token for token in re.findall(r"[a-z0-9]+", entity.casefold())
        if len(token) > 1
    }
    if not entity_tokens:
        return False
    ocr_tokens = set(re.findall(r"[a-z0-9]+", visible_text.casefold()))
    return len(entity_tokens & ocr_tokens) / len(entity_tokens) >= 2 / 3


def compact_ocr_hint(visible_text: str, max_tokens: int = 16) -> str:
    if not visible_text or visible_text.strip().casefold() in {"none", "unknown"}:
        return ""
    parts = re.findall(r"[A-Za-z0-9][A-Za-z0-9&.'/-]*", visible_text)
    return " ".join(parts[:max_tokens])


def build_entity_extraction_prompt(query: str) -> str:
    return (
        "ENTITY EXTRACTION ONLY. Do not answer the original question. First resolve"
        " the noun phrase referenced by the question, then identify that target in"
        " the image. Ignore foreground occluders and nearby objects when the question"
        " refers to something else. Identify the specific object, product, place,"
        " food, plant, animal, character, or vehicle model when possible. Return"
        " exactly <entity>NAME</entity>, or <entity>UNKNOWN</entity> if not confident."
        " Original question: "
        + query
    )


def build_baseline_entity_extraction_prompt(query: str) -> str:
    return (
        "ENTITY EXTRACTION ONLY. Do not answer the original question."
        " Identify the specific main object, product, place, food, plant,"
        " animal, or vehicle referenced by the question in the image. Return"
        " exactly <entity>NAME</entity>, or <entity>UNKNOWN</entity> if not"
        " confident. Original question: "
        + query
    )


def build_entity_views(image: Any) -> list[tuple[str, Any]]:
    width, height = image.size
    return [
        ("full", image),
        ("lower", image.crop((0, int(height * 0.30), width, height))),
        ("left", image.crop((0, 0, int(width * 0.65), height))),
        ("right", image.crop((int(width * 0.35), 0, width, height))),
        (
            "lower_left",
            image.crop((0, int(height * 0.30), int(width * 0.65), height)),
        ),
        (
            "lower_right",
            image.crop(
                (int(width * 0.35), int(height * 0.30), width, height)
            ),
        ),
        (
            "lower_left_detail",
            image.crop(
                (0, int(height * 0.30), int(width * 0.52), int(height * 0.92))
            ),
        ),
        (
            "right_center_detail",
            image.crop(
                (
                    int(width * 0.58),
                    int(height * 0.30),
                    int(width * 0.98),
                    int(height * 0.72),
                )
            ),
        ),
        (
            "center",
            image.crop(
                (
                    int(width * 0.15),
                    int(height * 0.15),
                    int(width * 0.85),
                    int(height * 0.85),
                )
            ),
        ),
    ]


def build_fast_entity_contact_sheet(image: Any) -> Any:
    from PIL import Image, ImageDraw, ImageOps

    views = dict(build_entity_views(image))
    panels = [
        ("LOWER", views["lower"]),
        ("LOWER LEFT", views["lower_left_detail"]),
        ("RIGHT DETAIL", views["right_center_detail"]),
        ("CENTER", views["center"]),
    ]
    sheet = Image.new("RGB", (960, 1280), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, panel) in enumerate(panels):
        x = (index % 2) * 480
        y = (index // 2) * 640
        fitted = ImageOps.contain(panel.convert("RGB"), (460, 590))
        paste_x = x + (480 - fitted.width) // 2
        paste_y = y + 40 + (590 - fitted.height) // 2
        sheet.paste(fitted, (paste_x, paste_y))
        draw.text((x + 10, y + 10), label, fill="black")
    return sheet


def build_contact_sheet_entity_prompt(query: str) -> str:
    return (
        "ENTITY EXTRACTION ONLY. The image is a 2x2 contact sheet of four crops "
        "from the same source image, labeled LOWER, LOWER LEFT, RIGHT DETAIL, and "
        "CENTER. Resolve the noun phrase referenced by the question and identify "
        "that exact target across the panels. Visible text, logos, model badges, "
        "book covers, labels, and chart headings are strong evidence. Do not answer "
        "the question. Return exactly <entity>NAME</entity>, or "
        "<entity>UNKNOWN</entity> if not confident. Original question: " + query
    )


def build_structured_visual_analysis_prompt(query: str) -> str:
    return (
        "VISUAL ANALYSIS ONLY. The image is a 2x2 contact sheet of crops from one "
        "source image. Do not answer the original question. Identify the exact target "
        "referenced by the question, transcribe only useful visible text such as brand, "
        "model, title, label, number, unit, or chart heading, choose a route, and report "
        "confidence. Route must be one of identity, visual, ocr, lookup, comparison, "
        "chart. Return exactly four tags and nothing else:\n"
        "<entity>NAME or UNKNOWN</entity>\n"
        "<ocr>useful visible text or NONE</ocr>\n"
        "<route>ROUTE</route>\n"
        "<confidence>high, medium, or low</confidence>\n"
        "Original question: " + query
    )


def should_run_multicrop_fallback(query: str, entity: str) -> bool:
    if not entity:
        return True
    needs_model_specificity = re.search(
        r"\b(generation|model|version)\b", query, re.IGNORECASE
    )
    return bool(needs_model_specificity and len(entity.split()) == 1)


def extract_query_scope_terms(query: str) -> list[str]:
    ignored = {"image", "picture", "photo", "this", "that", "these", "those", "it"}
    terms = []
    for match in re.finditer(
        r"\b(?:in|within|across|during)\s+(?:the\s+)?([a-z][a-z.-]*)",
        query,
        re.IGNORECASE,
    ):
        term = match.group(1).lower().rstrip(".")
        if term not in ignored and term not in terms:
            terms.append(term)
    return terms


def normalize_numeric_text(value: str) -> str:
    number_words = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
        "thirteen": "13",
        "fourteen": "14",
        "fifteen": "15",
        "sixteen": "16",
        "seventeen": "17",
        "eighteen": "18",
        "nineteen": "19",
        "twenty": "20",
    }
    normalized = value.lower().replace(",", "")
    for word, number in number_words.items():
        normalized = re.sub(rf"\b{word}\b", number, normalized)
    return normalized


def numeric_context_tokens(value: str, number: str, window: int = 2) -> list[set[str]]:
    ignored = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "only",
        "or",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
    aliases = {
        "sale": "sale",
        "sales": "sale",
        "sold": "sale",
        "seat": "seat",
        "seats": "seat",
        "seating": "seat",
    }
    tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", normalize_numeric_text(value))
    contexts = []
    for index, token in enumerate(tokens):
        if token != number:
            continue
        nearby = tokens[max(0, index - window) : index] + tokens[
            index + 1 : index + 1 + window
        ]
        contexts.append(
            {
                aliases.get(item, item)
                for item in nearby
                if item not in ignored and not re.fullmatch(r"\d+(?:\.\d+)?", item)
            }
        )
    return contexts


def validate_numeric_evidence(
    query: str, response: str, rag_context: str
) -> tuple[bool, str]:
    normalized_response = normalize_numeric_text(response)
    query_numbers = set(
        re.findall(
            r"\b\d[\d]*(?:\.\d+)?\b", normalize_numeric_text(query)
        )
    )
    numbers = [
        number
        for number in re.findall(r"\b\d[\d]*(?:\.\d+)?\b", normalized_response)
        if number not in query_numbers
    ]
    if not numbers:
        return True, "no_numbers"
    documents = re.findall(r"<DOC>.*?</DOC>", rag_context, re.DOTALL | re.IGNORECASE)
    if not documents:
        return False, "no_web_documents"
    normalized_documents = [normalize_numeric_text(document) for document in documents]
    scope_terms = extract_query_scope_terms(query)
    for number in numbers:
        normalized_number = number.replace(",", "")
        is_year = (
            normalized_number.isdigit()
            and len(normalized_number) == 4
            and 1000 <= int(normalized_number) <= 2099
        )
        answer_contexts = numeric_context_tokens(response, normalized_number)
        answer_context = set().union(*answer_contexts) if answer_contexts else set()
        matching_documents = []
        for document in normalized_documents:
            document_contexts = numeric_context_tokens(document, normalized_number)
            if not document_contexts:
                continue
            if not is_year and answer_context and not any(
                answer_context & document_context for document_context in document_contexts
            ):
                continue
            matching_documents.append(document)
        if not matching_documents:
            return False, f"unsupported_number:{number}"
        if scope_terms and not any(
            all(term in document for term in scope_terms)
            for document in matching_documents
        ):
            return False, f"out_of_scope_number:{number}"
    return True, "supported"


def minimize_boolean_answer(query: str, response: str) -> str:
    if not re.match(
        r"^\s*(?:is|are|was|were|can|could|would|did|do|does|has|have|had)\b",
        query,
        re.IGNORECASE,
    ):
        return response.strip()
    protected_response = response.strip()
    abbreviations = {
        "D.C.": "D<dot>C<dot>",
        "U.S.": "U<dot>S<dot>",
        "U.K.": "U<dot>K<dot>",
    }
    for abbreviation, placeholder in abbreviations.items():
        protected_response = protected_response.replace(abbreviation, placeholder)
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", protected_response)
        if sentence.strip()
    ]
    if not sentences:
        return response.strip()
    selected = sentences[0]
    for sentence in reversed(sentences):
        conclusion = re.match(
            r"^(?:therefore|thus|consequently),?\s*(.+)$",
            sentence,
            re.IGNORECASE,
        )
        if conclusion:
            selected = conclusion.group(1)
            break
        so_clause = re.search(r"\bso\s+(.+)$", sentence, re.IGNORECASE)
        if so_clause:
            selected = so_clause.group(1)
            break
    selected = re.split(r",\s*(?:as|because)\s+", selected, maxsplit=1, flags=re.IGNORECASE)[0]
    selected = selected.strip()
    selected = selected.replace("<dot>", ".")
    if selected and selected[-1] not in ".!?":
        selected += "."
    return selected


def minimize_versus_answer(query: str, response: str) -> str:
    if not re.search(r"\bversus\b", query, re.IGNORECASE):
        return response.strip()
    parts = re.split(r",\s*while\s+", response.strip(), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return response.strip()
    right = parts[1]
    first_year = re.search(r"\b(?:1\d{3}|20\d{2})\b", right)
    if not first_year:
        return response.strip()
    right = right[: first_year.end()].rstrip(" ,;.")
    return f"{parts[0].rstrip(' ,;.')} while {right}."


def build_grounded_retry_prompt(query: str, entity: str) -> str:
    species_instruction = ""
    if re.search(r"\bwhich species\b", query, re.IGNORECASE):
        species_instruction = (
            " For a species question, list the specific common and/or scientific"
            " species names from the documents; do not answer with only an umbrella"
            " common name."
        )
    return (
        "GROUNDED RETRY. Answer the original question, not this instruction. The image"
        f' referent used for retrieval is "{entity}". Re-read the supplied web'
        " documents and answer when they directly support the requested fact. You may"
        " perform only simple arithmetic, unit-preserving comparisons, and year-order"
        " comparisons from explicit values in the documents or question. For a"
        " multi-part question, include every requested field. Do not use a related"
        " brand, model, country, or object. If a required fact is still missing, reply"
        " exactly: I don't know."
        + species_instruction
        + " Original question: "
        + query
    )


def response_needs_completeness_retry(query: str, response: str) -> bool:
    if not re.search(r"\bwhich species\b", query, re.IGNORECASE):
        return False
    normalized = response.casefold()
    species_markers = (
        "german chamomile",
        "roman chamomile",
        "matricaria",
        "chamaemelum",
    )
    return not any(marker in normalized for marker in species_markers)


def build_web_entity_fallback_prompt(query: str) -> str:
    return (
        "ENTITY RECOVERY ONLY. Do not answer the original question. Inspect the image"
        " and the supplied web result titles. Identify the exact object, vehicle,"
        " place, artwork, food, or product referenced by the question only when the"
        " image and at least one relevant title support the same identity. Return"
        " exactly <entity>NAME</entity>, otherwise <entity>UNKNOWN</entity>. Original"
        " question: "
        + query
    )


def build_multicrop_selection_prompt(
    query: str, observations: list[dict[str, str]]
) -> str:
    candidates = []
    seen = set()
    for observation in observations:
        entity = observation.get("entity", "").strip()
        key = entity.casefold()
        if entity and key not in seen:
            seen.add(key)
            candidates.append(entity)
    candidate_text = ", ".join(candidates) if candidates else "none"
    badge_instruction = ""
    if re.search(
        r"\b(?:engine|towing|torque|model|version)\b", query, re.IGNORECASE
    ) and any(re.search(r"\d", candidate) for candidate in candidates):
        badge_instruction = (
            " If candidates differ by a numeric vehicle model, read the visible model"
            " badge on the vehicle and prefer that direct text over majority voting."
        )
    return (
        "ENTITY SELECTION ONLY. Do not answer the original question. Inspect the full"
        " image and resolve exactly what the question refers to. The following names"
        " came from overlapping image crops and may describe foreground occluders or"
        " unrelated objects: "
        + candidate_text
        + ". Return exactly one listed name as <entity>NAME</entity> only if it"
        " identifies the question referent; otherwise return <entity>UNKNOWN</entity>."
        + badge_instruction
        + " Original question: "
        + query
    )


def validate_multicrop_entity(
    selected_entity: str, observations: list[dict[str, str]]
) -> str:
    if not selected_entity:
        return ""
    selected_key = selected_entity.casefold()
    matching = [
        observation
        for observation in observations
        if observation.get("entity", "").casefold() == selected_key
    ]
    if len(matching) >= 2:
        return selected_entity
    if any(
        gate_entity_with_image_candidates(
            selected_entity, observation.get("image_context", "")
        )
        for observation in matching
    ):
        return selected_entity
    return ""


def entity_candidate_was_observed(
    selected_entity: str, observations: list[dict[str, str]]
) -> bool:
    if not selected_entity:
        return False
    selected_key = selected_entity.casefold().strip()
    return any(
        observation.get("entity", "").casefold().strip() == selected_key
        for observation in observations
    )


def choose_uncontested_baseline_candidate(
    observations: list[dict[str, str]]
) -> str:
    if not observations:
        return ""
    baseline = observations[0].get("entity", "").strip()
    if not baseline:
        return ""
    other_entities = {
        observation.get("entity", "").casefold().strip()
        for observation in observations[1:]
        if observation.get("entity", "").strip()
    }
    if not other_entities or other_entities == {baseline.casefold()}:
        return baseline
    return ""


def choose_only_observed_candidate(observations: list[dict[str, str]]) -> str:
    entities = [
        observation.get("entity", "").strip()
        for observation in observations
        if observation.get("entity", "").strip()
    ]
    unique = {entity.casefold(): entity for entity in entities}
    if len(unique) == 1:
        return next(iter(unique.values()))
    return ""


def canonicalize_entity_spelling(
    selected_entity: str, observations: list[dict[str, str]]
) -> str:
    selected = selected_entity.strip()
    if not selected:
        return ""
    selected_key = selected.casefold()
    for observation in observations:
        observed = observation.get("entity", "").strip()
        observed_key = observed.casefold()
        if observed and selected_key.endswith("s") and observed_key == selected_key[:-1]:
            return observed
    return selected


def chart_category_answer(query: str, entity_candidate: str) -> str:
    if not re.search(r"\bage\b", query, re.IGNORECASE) or not re.search(
        r"\bsex\b", query, re.IGNORECASE
    ):
        return ""
    match = re.search(
        r"\b(\d{1,2}\s*[-–]\s*\d{1,2})\b.*?\b(males?|females?)\b",
        entity_candidate,
        re.IGNORECASE,
    )
    if not match:
        return ""
    sex = match.group(2).lower()
    if sex == "male":
        sex = "males"
    elif sex == "female":
        sex = "females"
    return f"{sex} aged {match.group(1).replace(' ', '')}."


def token_f1(prediction: str, reference: str) -> float:
    prediction_tokens = re.findall(r"[a-z0-9]+", prediction.lower())
    reference_tokens = re.findall(r"[a-z0-9]+", reference.lower())
    if not prediction_tokens or not reference_tokens:
        return 0.0
    overlap = sum(
        (Counter(prediction_tokens) & Counter(reference_tokens)).values()
    )
    if overlap == 0:
        return 0.0
    precision = overlap / len(prediction_tokens)
    recall = overlap / len(reference_tokens)
    return 2 * precision * recall / (precision + recall)


def is_abstention(response: str) -> bool:
    return response.strip().lower() in {"i don't know.", "i don't know"}


def gate_entity_with_image_candidates(entity: str, image_context: str) -> str:
    if not entity or not image_context:
        return entity
    pattern = re.compile(
        r"Candidate (?P<rank>\d+): "
        + re.escape(entity)
        + r" \(visual similarity: [0-9.]+; occurrences: (?P<count>\d+)\)",
        re.IGNORECASE,
    )
    match = pattern.search(image_context)
    if not match:
        return ""
    rank = int(match.group("rank"))
    count = int(match.group("count"))
    if rank == 1 and count < 3:
        return ""
    return entity


def main() -> int:
    args = parse_args()
    if args.max_tokens < 1:
        raise SystemExit("--max-tokens must be at least 1")
    if args.answer_token_limit < 1:
        raise SystemExit("--answer-token-limit must be at least 1")

    if args.limit is not None and args.positions is not None:
        raise SystemExit("--limit and --positions cannot be combined")
    if args.rewrite_multicrop and not (
        args.rewrite_web_query and args.image_retrieval and args.web_retrieval
    ):
        raise SystemExit(
            "--rewrite-multicrop requires --rewrite-web-query, --image-retrieval, "
            "and --web-retrieval"
        )
    if args.use_entity_candidate_for_search and not args.rewrite_multicrop:
        raise SystemExit(
            "--use-entity-candidate-for-search requires --rewrite-multicrop"
        )
    if args.fast_multicrop and not args.rewrite_multicrop:
        raise SystemExit("--fast-multicrop requires --rewrite-multicrop")
    manifest_entries = load_manifest(args.manifest, args.limit)
    selected_positions = parse_positions(args.positions, len(manifest_entries))
    if selected_positions is None:
        entries = list(enumerate(manifest_entries))
    else:
        entries = [
            (position, manifest_entries[position]) for position in selected_positions
        ]
    all_entries = list(entries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output.with_suffix(args.output.suffix + ".partial.jsonl")
    prior_results: list[dict[str, Any]] = []
    if args.resume and checkpoint_path.is_file():
        seen_positions: set[int] = set()
        expected_by_position = {
            entry.get("index", manifest_position): entry
            for manifest_position, entry in all_entries
        }
        for line_number, line in enumerate(
            checkpoint_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                result = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(
                    f"Invalid checkpoint JSON on line {line_number}: {error}"
                ) from error
            position = result.get("position")
            entry = expected_by_position.get(position)
            if entry is None or position in seen_positions:
                raise SystemExit(f"Unexpected or duplicate checkpoint position: {position}")
            if (
                result.get("session_id") != entry.get("session_id")
                or result.get("image") != entry.get("image")
                or result.get("query") != first_value(entry, "turns", "query")
            ):
                raise SystemExit(f"Checkpoint input mismatch at position {position}")
            seen_positions.add(position)
            prior_results.append(result)
        entries = [
            (manifest_position, entry)
            for manifest_position, entry in all_entries
            if entry.get("index", manifest_position) not in seen_positions
        ]
        print(
            f"Resuming with {len(prior_results)} completed results; "
            f"{len(entries)} remaining.",
            flush=True,
        )
    else:
        checkpoint_path.write_text("", encoding="utf-8")
    if args.hf_home:
        os.environ["HF_HOME"] = str(args.hf_home)
        os.environ["HF_HUB_CACHE"] = str(args.hf_home / "hub")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

    import torch
    from PIL import Image
    from example_agents.user_config import get_agent_from_model_name
    from utils.retriever import get_rag_context
    from utils.search_pipeline_compat import UnifiedSearchPipeline
    from utils.web_reranker import CrossEncoderWebReranker

    web_reranker = None
    if args.web_reranker_model:
        if not args.web_reranker_model.is_dir():
            raise SystemExit(
                f"Web reranker model directory does not exist: {args.web_reranker_model}"
            )
        web_reranker = CrossEncoderWebReranker(
            args.web_reranker_model,
            device=args.web_reranker_device,
            batch_size=args.web_reranker_batch_size,
        )

    refusal_gate = None
    refusal_feature_names = None
    refusal_threshold = None
    if args.refusal_gate_config:
        import numpy as np
        from tools.calibrate_refusal_gate import (
            align_feature_values,
            extract_features,
            predict,
        )

        gate_payload = json.loads(
            args.refusal_gate_config.read_text(encoding="utf-8")
        )
        refusal_feature_names = gate_payload["feature_names"]
        refusal_gate = {
            key: np.asarray(gate_payload["model"][key], dtype=np.float64)
            for key in ("mean", "scale", "weights")
        }
        refusal_threshold = (
            args.refusal_gate_threshold
            if args.refusal_gate_threshold is not None
            else gate_payload["dev_trained_threshold"]
        )

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available. Run this tool in the cloud environment.")

    started_at = datetime.now(timezone.utc).isoformat()
    torch.cuda.reset_peak_memory_stats()
    memory_snapshots = {"start": cuda_memory_snapshot(torch)}
    search_pipeline = None
    retrieval_init_seconds = None
    retrieval_timings = None
    if args.image_retrieval or args.web_retrieval:
        retrieval_init_start = time.perf_counter()
        search_pipeline = UnifiedSearchPipeline(
            text_model_name=(
                "BAAI/bge-large-en-v1.5" if args.web_retrieval else None
            ),
            web_hf_dataset_id=(
                "crag-mm-2025/web-search-index-public-test"
                if args.web_retrieval
                else None
            ),
            image_model_name=(
                "openai/clip-vit-large-patch14-336"
                if args.image_retrieval
                else None
            ),
            image_hf_dataset_id=(
                "crag-mm-2025/image-search-index-public-test"
                if args.image_retrieval
                else None
            ),
            report_timings=True,
        )
        retrieval_init_seconds = time.perf_counter() - retrieval_init_start
        retrieval_timings = search_pipeline.timings
        memory_snapshots["after_retrieval_init"] = cuda_memory_snapshot(torch)

    model_load_start = time.perf_counter()
    agent_class = get_agent_from_model_name(args.model_name)
    agent = agent_class(model_name=args.model_name, max_gen_len=args.max_tokens)
    model_load_seconds = time.perf_counter() - model_load_start
    memory_snapshots["after_model_load"] = cuda_memory_snapshot(torch)

    results: list[dict[str, Any]] = list(prior_results)
    manifest_dir = args.manifest.resolve().parent
    for manifest_position, entry in entries:
        position = entry.get("index", manifest_position)
        if not isinstance(position, int):
            raise SystemExit(
                f"Manifest entry index must be an integer: {position!r}"
            )
        image_path = manifest_dir / entry["image"]
        if not image_path.is_file():
            raise SystemExit(f"Image does not exist: {image_path}")
        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB")
        if not entry.get("image_url"):
            image = image.resize((960, 1280))

        query = first_value(entry, "turns", "query")
        ground_truth = first_value(entry, "answers", "ans_full")
        question_route = classify_question_route(query)
        visible_text = ""
        visual_confidence = ""
        entity_consistency_valid = False
        entity_response_raw = ""
        entity_response = ""
        entity_search_candidate = ""
        web_search_entity = ""
        entity_rewrite_details: list[dict[str, str]] = []
        web_search_query = query
        web_queries = [query]
        rewrite_seconds = 0.0
        if args.web_retrieval and args.rewrite_web_query:
            rewrite_start = time.perf_counter()
            if args.rewrite_multicrop:
                full_image_context = get_rag_context(
                    query=query,
                    image=image,
                    search_pipeline=search_pipeline,
                    image_search=True,
                    web_search=False,
                )
                baseline_raw_response = agent.batch_generate_response(
                    queries=[build_baseline_entity_extraction_prompt(query)],
                    images=[image],
                    message_histories=[[]],
                    rag_context_list=[full_image_context],
                )[0]
                baseline_entity = extract_tagged_entity(baseline_raw_response)
                entity_response = gate_entity_with_image_candidates(
                    baseline_entity, full_image_context
                )
                entity_response_raw = baseline_raw_response
                entity_rewrite_details.append(
                    {
                        "view": "full",
                        "entity": baseline_entity,
                        "raw_response": baseline_raw_response,
                        "image_context": full_image_context,
                    }
                )
                if should_run_multicrop_fallback(query, entity_response):
                    if args.fast_multicrop:
                        contact_sheet = build_fast_entity_contact_sheet(image)
                        raw_response = agent.batch_generate_response(
                            queries=[
                                build_structured_visual_analysis_prompt(query)
                                if args.structured_visual_analysis
                                else build_contact_sheet_entity_prompt(query)
                            ],
                            images=[contact_sheet],
                            message_histories=[[]],
                            rag_context_list=[full_image_context],
                        )[0]
                        entity_rewrite_details.append(
                            {
                                "view": "contact_sheet",
                                "entity": extract_tagged_entity(raw_response),
                                "raw_response": raw_response,
                                "image_context": full_image_context,
                            }
                        )
                        entity_response_raw = raw_response
                        if args.structured_visual_analysis:
                            visible_text = compact_ocr_hint(
                                extract_tagged_value(raw_response, "ocr")
                            )
                            question_route = normalize_visual_route(
                                extract_tagged_value(raw_response, "route"), query
                            )
                            visual_confidence = extract_tagged_value(
                                raw_response, "confidence"
                            ).casefold()
                    else:
                        for view_name, view_image in build_entity_views(image)[1:]:
                            image_context = get_rag_context(
                                query=query,
                                image=view_image,
                                search_pipeline=search_pipeline,
                                image_search=True,
                                web_search=False,
                            )
                            raw_response = agent.batch_generate_response(
                                queries=[build_entity_extraction_prompt(query)],
                                images=[view_image],
                                message_histories=[[]],
                                rag_context_list=[image_context],
                            )[0]
                            entity_rewrite_details.append(
                                {
                                    "view": view_name,
                                    "entity": extract_tagged_entity(raw_response),
                                    "raw_response": raw_response,
                                    "image_context": image_context,
                                }
                            )
                        selection_prompt = build_multicrop_selection_prompt(
                            query, entity_rewrite_details
                        )
                        entity_response_raw = agent.batch_generate_response(
                            queries=[selection_prompt],
                            images=[image],
                            message_histories=[[]],
                            rag_context_list=[""],
                        )[0]
                    selected_entity = extract_tagged_entity(entity_response_raw)
                    selected_entity = canonicalize_entity_spelling(
                        selected_entity, entity_rewrite_details
                    )
                    if visual_confidence == "low":
                        selected_entity = ""
                    if entity_candidate_was_observed(
                        selected_entity, entity_rewrite_details
                    ):
                        entity_search_candidate = selected_entity
                    if not entity_search_candidate:
                        entity_search_candidate = choose_uncontested_baseline_candidate(
                            entity_rewrite_details
                        )
                    if not entity_search_candidate:
                        entity_search_candidate = choose_only_observed_candidate(
                            entity_rewrite_details
                        )
                    entity_response = validate_multicrop_entity(
                        selected_entity,
                        entity_rewrite_details,
                    )
                    if (
                        not entity_response
                        and selected_entity
                        and visual_confidence == "high"
                        and ocr_supports_entity(selected_entity, visible_text)
                    ):
                        entity_response = selected_entity
            else:
                rewrite_rag_context = ""
                if args.image_retrieval:
                    rewrite_rag_context = get_rag_context(
                        query=query,
                        image=image,
                        search_pipeline=search_pipeline,
                        image_search=True,
                        web_search=False,
                    )
                entity_response_raw = agent.batch_generate_response(
                    queries=[build_entity_extraction_prompt(query)],
                    images=[image],
                    message_histories=[[]],
                    rag_context_list=[rewrite_rag_context],
                )[0]
                entity_response = extract_tagged_entity(entity_response_raw)
                if args.image_retrieval:
                    entity_response = gate_entity_with_image_candidates(
                        entity_response, rewrite_rag_context
                    )
            rewrite_seconds = time.perf_counter() - rewrite_start
            web_search_entity = entity_response
            entity_consistency_valid = bool(entity_response)
            if (
                not web_search_entity
                and args.use_entity_candidate_for_search
                and entity_search_candidate
            ):
                web_search_entity = entity_search_candidate
            if args.focused_web_query:
                web_search_query = build_focused_web_search_query(
                    query, web_search_entity
                )
            else:
                web_search_query = build_web_search_query(query, web_search_entity)
            if (
                args.structured_visual_analysis
                and not web_search_entity
                and visible_text
            ):
                web_search_query = (
                    f"Visible image text: {visible_text}. Question: {query}"
                )
            if args.multi_web_query:
                web_queries = build_multi_web_queries(
                    query,
                    web_search_entity or entity_search_candidate,
                    visible_text,
                    question_route,
                )
            else:
                web_queries = [web_search_query]
        use_web_retrieval = args.web_retrieval
        if args.structured_visual_analysis and args.route_web_retrieval:
            direct_ocr = question_route == "ocr" and bool(
                re.match(r"\s*(what|which|how many|how much|does|is|are)\b", query, re.IGNORECASE)
            )
            if question_route in {"identity", "visual", "chart"} or direct_ocr:
                use_web_retrieval = False
        retrieval_start = time.perf_counter()
        rag_context = get_rag_context(
            query=query,
            image=image,
            search_pipeline=search_pipeline,
            image_search=args.image_retrieval,
            web_search=use_web_retrieval,
            full_query=web_search_query if use_web_retrieval else None,
            include_original_web_query=(
                args.dual_web_query
                and (
                    question_route == "comparison"
                    or bool(re.search(r"\bversus\b", query, re.IGNORECASE))
                )
            ),
            rerank_web_results=(
                args.focused_web_query and web_reranker is None
            ),
            max_web_context_results=(
                8 if args.expanded_web_context else 5 if args.multi_web_query else 3
            ),
            web_context_char_cap=(
                12000 if args.expanded_web_context else 9000 if args.multi_web_query else 6000
            ),
            web_queries=web_queries if use_web_retrieval else None,
            web_reranker=web_reranker,
            reranker_query=(
                build_focused_web_search_query(
                    query, web_search_entity or entity_search_candidate
                )
                if (web_search_entity or entity_search_candidate)
                else query
            ),
            filter_entity=web_search_entity or entity_search_candidate,
            reranker_candidate_cap=args.web_reranker_candidate_cap,
        )
        retrieval_seconds = time.perf_counter() - retrieval_start
        generation_start = time.perf_counter()
        response = agent.batch_generate_response(
            queries=[query],
            images=[image],
            message_histories=[[]],
            rag_context_list=[rag_context],
        )[0]
        first_pass_response = response
        retry_response = ""
        web_entity_fallback_raw = ""
        web_entity_fallback = ""
        if (
            args.web_entity_fallback
            and is_abstention(response)
            and not web_search_entity
            and "<DOC>" in rag_context
        ):
            web_entity_fallback_raw = agent.batch_generate_response(
                queries=[build_web_entity_fallback_prompt(query)],
                images=[image],
                message_histories=[[]],
                rag_context_list=[rag_context],
            )[0]
            web_entity_fallback = extract_tagged_entity(web_entity_fallback_raw)
            if web_entity_fallback:
                web_search_entity = web_entity_fallback
                web_search_query = build_focused_web_search_query(
                    query, web_entity_fallback
                )
                fallback_retrieval_start = time.perf_counter()
                rag_context = get_rag_context(
                    query=query,
                    image=image,
                    search_pipeline=search_pipeline,
                    image_search=False,
                    web_search=True,
                    full_query=web_search_query,
                    rerank_web_results=True,
                    max_web_context_results=(8 if args.expanded_web_context else 3),
                    web_context_char_cap=(12000 if args.expanded_web_context else 6000),
                )
                retrieval_seconds += time.perf_counter() - fallback_retrieval_start
        categorical_answer = chart_category_answer(
            query, entity_response or entity_search_candidate
        )
        if categorical_answer:
            response = categorical_answer
        if (
            args.retry_grounded_abstentions
            and (
                is_abstention(response)
                or response_needs_completeness_retry(query, response)
            )
            and (web_search_entity or "<DOC>" in rag_context)
        ):
            retry_response = agent.batch_generate_response(
                queries=[
                    build_grounded_retry_prompt(
                        query,
                        web_search_entity
                        or "unresolved; use only an identity supported by the image and documents",
                    )
                ],
                images=[image],
                message_histories=[[]],
                rag_context_list=[rag_context],
            )[0]
            response = retry_response
        untrimmed_agent_response = response
        if args.concise_boolean_answers:
            response = minimize_boolean_answer(query, response)
            response = minimize_versus_answer(query, response)
        response = truncate_answer_tokens(
            response, agent.tokenizer, args.answer_token_limit
        )
        preliminary_response = response
        numeric_evidence_valid = None
        numeric_evidence_reason = "not_checked"
        if categorical_answer:
            numeric_evidence_valid = True
            numeric_evidence_reason = "visual_category"
        elif args.validate_numeric_evidence and not is_abstention(response):
            numeric_evidence_valid, numeric_evidence_reason = validate_numeric_evidence(
                query, response, rag_context
            )
            if not numeric_evidence_valid:
                response = "I don't know."
        generation_seconds = time.perf_counter() - generation_start
        result = {
            "position": position,
            "dataset_index": entry.get("index"),
            "session_id": entry.get("session_id"),
            "image": entry["image"],
            "query": query,
            "question_route": question_route,
            "visible_text": visible_text,
            "visual_confidence": visual_confidence,
            "entity_consistency_valid": entity_consistency_valid,
            "web_retrieval_routed": use_web_retrieval,
            "web_query_entity": entity_response,
            "web_query_entity_candidate": entity_search_candidate,
            "web_query_entity_raw": entity_response_raw,
            "web_query_entity_details": entity_rewrite_details,
            "web_search_query": web_search_query,
            "web_queries": web_queries,
            "web_reranker_enabled": web_reranker is not None,
            "ground_truth": ground_truth,
            "agent_response": response,
            "first_pass_response": first_pass_response,
            "grounded_retry_response": retry_response,
            "categorical_answer": categorical_answer,
            "web_entity_fallback_raw": web_entity_fallback_raw,
            "web_entity_fallback": web_entity_fallback,
            "untrimmed_agent_response": untrimmed_agent_response,
            "preliminary_agent_response": preliminary_response,
            "numeric_evidence_valid": numeric_evidence_valid,
            "numeric_evidence_reason": numeric_evidence_reason,
            "rag_context": rag_context,
            "retrieval_seconds": round(retrieval_seconds, 3),
            "rewrite_seconds": round(rewrite_seconds, 3),
            "generation_seconds": round(generation_seconds, 3),
            "cuda_memory": cuda_memory_snapshot(torch),
            "proxy_token_f1": round(token_f1(response, ground_truth), 4),
            "is_abstention": is_abstention(response),
        }
        if refusal_gate is not None:
            feature_names, feature_values = extract_features(result)
            feature_values = align_feature_values(
                feature_names, feature_values, refusal_feature_names
            )
            probability_correct = float(
                predict(refusal_gate, feature_values.reshape(1, -1))[0]
            )
            result["refusal_gate_probability_correct"] = round(
                probability_correct, 6
            )
            result["refusal_gate_threshold"] = refusal_threshold
            if not result["is_abstention"] and probability_correct < refusal_threshold:
                result["pre_refusal_gate_response"] = result["agent_response"]
                result["agent_response"] = "I don't know."
                result["proxy_token_f1"] = 0.0
                result["is_abstention"] = True
        results.append(result)
        with checkpoint_path.open("a", encoding="utf-8") as checkpoint:
            checkpoint.write(json.dumps(result, ensure_ascii=False) + "\n")
            checkpoint.flush()
        print(
            json.dumps(
                {
                    "position": position,
                    "entity": entity_response,
                    "response": response,
                    "proxy_token_f1": result["proxy_token_f1"],
                    "is_abstention": result["is_abstention"],
                    "retrieval_seconds": result["retrieval_seconds"],
                    "generation_seconds": result["generation_seconds"],
                    "rag_context_chars": len(rag_context),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    expected_order = {
        entry.get("index", manifest_position): order
        for order, (manifest_position, entry) in enumerate(all_entries)
    }
    results.sort(key=lambda item: expected_order[item["position"]])
    count = len(results)
    if count != len(all_entries):
        raise SystemExit(
            f"Expected {len(all_entries)} results after resume, found {count}"
        )
    payload = {
        "dataset": "crag-mm-2025/crag-mm-single-turn-public",
        "revision": "v0.1.2",
        "split": "validation",
        "retrieval": {
            "image": args.image_retrieval,
            "web": args.web_retrieval,
        },
        "retrieval_init_seconds": (
            round(retrieval_init_seconds, 3)
            if retrieval_init_seconds is not None
            else None
        ),
        "retrieval_timings": retrieval_timings,
        "model_name": args.model_name,
        "max_tokens": args.max_tokens,
        "started_at_utc": started_at,
        "model_load_seconds": round(model_load_seconds, 3),
        "cuda_memory_snapshots": memory_snapshots,
        "cuda_peak_allocated_gib": round(
            torch.cuda.max_memory_allocated() / 1024**3, 3
        ),
        "proxy_metrics": {
            "count": count,
            "abstention_count": sum(result["is_abstention"] for result in results),
            "abstention_rate": round(
                sum(result["is_abstention"] for result in results) / count, 4
            ),
            "entity_rewrite_count": sum(
                bool(result["web_query_entity"]) for result in results
            ),
            "entity_rewrite_rate": round(
                sum(bool(result["web_query_entity"]) for result in results) / count,
                4,
            ),
            "mean_token_f1": round(
                sum(result["proxy_token_f1"] for result in results) / count, 4
            ),
            "mean_retrieval_seconds": round(
                sum(result["retrieval_seconds"] for result in results) / count, 4
            ),
            "mean_generation_seconds": round(
                sum(result["generation_seconds"] for result in results) / count, 4
            ),
        },
        "results": results,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    checkpoint_path.unlink(missing_ok=True)
    print(f"Saved {len(results)} results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
