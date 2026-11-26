# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import sys
from collections import Counter
import math
import re

from utils.crag_web_result_fetcher import WebSearchResult
from utils.search_pipeline_compat import UnifiedSearchPipeline
from PIL import Image

NUM_IMG_SEARCH_RESULTS = 15
MAX_IMG_ENTITY_CANDIDATES = 8

NUM_WEB_SEARCH_RESULTS = 20
MAX_WEB_CONTEXT_RESULTS = 3
WEB_CONTEXT_CHAR_CAP = 6000
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.6


def _safe_str(value):
    encoding = sys.stdout.encoding or "utf-8"
    return str(value).encode(encoding, errors="replace").decode(encoding)


def _select_image_entity_candidates(image_search_results):
    """Return a short, de-duplicated list of plausible image entity names.

    The image index is useful for entity recognition, but its long attributes can
    dominate the visual prompt and turn a merely similar neighbor into asserted
    evidence. Keep only names and scores here; factual attributes should come from
    web retrieval after an entity has been identified confidently.
    """
    candidates = []
    occurrences = Counter()
    for result in image_search_results:
        if result.get("score", 0) <= IMG_SEARCH_CONFIDENCE_THRESHOLD:
            continue
        occurrences.update(
            entity.get("entity_name")
            for entity in result.get("entities", [])
            if entity.get("entity_name")
        )
    seen_names = set()
    for result in image_search_results:
        score = result.get("score", 0)
        if score <= IMG_SEARCH_CONFIDENCE_THRESHOLD:
            continue
        for entity in result.get("entities", []):
            entity_name = entity.get("entity_name")
            if not entity_name or entity_name in seen_names:
                continue
            seen_names.add(entity_name)
            candidates.append(
                {
                    "name": entity_name,
                    "score": score,
                    "occurrences": occurrences[entity_name],
                    "rank": len(candidates) + 1,
                }
            )
            if len(candidates) >= MAX_IMG_ENTITY_CANDIDATES:
                return candidates
    return candidates


def _merge_search_results(primary_results, secondary_results):
    merged = []
    seen = set()
    max_length = max(len(primary_results), len(secondary_results))
    for index in range(max_length):
        for results in (primary_results, secondary_results):
            if index >= len(results):
                continue
            result = results[index]
            key = (
                result.get("page_url")
                or result.get("page_id")
                or (result.get("page_name"), result.get("page_snippet"))
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(result)
    return merged


def _merge_many_search_results(result_groups):
    merged = []
    seen = set()
    max_length = max((len(group) for group in result_groups), default=0)
    for index in range(max_length):
        for group in result_groups:
            if index >= len(group):
                continue
            result = group[index]
            key = (
                result.get("page_url")
                or result.get("page_id")
                or (result.get("page_name"), result.get("page_snippet"))
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(result)
    return merged


def _filter_search_results(search_results, query, entity=""):
    if not search_results:
        return search_results
    ignored = {
        "a", "an", "and", "are", "car", "company", "image", "model", "of",
        "the", "this", "vehicle",
    }
    entity_tokens = {
        token for token in re.findall(r"[a-z0-9]+", entity.casefold())
        if len(token) > 1 and token not in ignored
    }
    scope_patterns = {
        "canada": ("canada", "canadian"),
        "united states": ("united states", "u.s.", "usa", "american"),
        "australia": ("australia", "australian"),
        "europe": ("europe", "european"),
        "japan": ("japan", "japanese"),
    }
    query_key = query.casefold()
    required_scopes = [
        variants
        for variants in scope_patterns.values()
        if any(variant in query_key for variant in variants)
    ]
    query_years = set(re.findall(r"\b(?:19|20)\d{2}\b", query_key))
    filtered = []
    for result in search_results:
        text = f"{result.get('page_name', '')} {result.get('page_snippet', '')}".casefold()
        tokens = set(re.findall(r"[a-z0-9]+", text))
        if entity_tokens and not (entity_tokens & tokens):
            continue
        if required_scopes and not all(
            any(variant in text for variant in variants)
            for variants in required_scopes
        ):
            continue
        if query_years and not (query_years & set(re.findall(r"\b(?:19|20)\d{2}\b", text))):
            continue
        filtered.append(result)
    return filtered if len(filtered) >= 3 else search_results


def _rerank_search_results(search_results, query):
    ignored = {
        "a", "an", "and", "are", "at", "for", "from", "how", "in", "is",
        "it", "of", "on", "the", "this", "to", "was", "were", "what",
        "when", "which", "who", "with",
    }
    aliases = {"tables": "table", "used": "use", "uses": "use"}
    query_tokens = [
        aliases.get(token, token[:-1] if token.endswith("s") and len(token) > 4 else token)
        for token in re.findall(r"[a-z0-9]+", query.casefold())
        if token not in ignored and len(token) > 1
    ]
    if not query_tokens or not search_results:
        return search_results
    result_tokens = []
    for result in search_results:
        text = f"{result.get('page_name', '')} {result.get('page_snippet', '')}"
        tokens = re.findall(r"[a-z0-9]+", text.casefold())
        result_tokens.append(
            {
                aliases.get(
                    token,
                    token[:-1] if token.endswith("s") and len(token) > 4 else token,
                )
                for token in tokens
            }
        )
    document_frequency = Counter(
        token for tokens in result_tokens for token in set(query_tokens) & tokens
    )
    count = len(search_results)

    def score(index):
        covered = set(query_tokens) & result_tokens[index]
        lexical_score = sum(
            math.log((count + 1) / (document_frequency[token] + 1)) + 1
            for token in covered
        )
        return lexical_score, -index

    ranked_indices = sorted(range(count), key=score, reverse=True)
    return [search_results[index] for index in ranked_indices]


def get_rag_context(
    query: str,
    image: Image.Image,
    search_pipeline: UnifiedSearchPipeline,
    image_search: bool,
    web_search: bool,
    full_query: str = None,
    include_original_web_query: bool = False,
    rerank_web_results: bool = False,
    max_web_context_results: int = MAX_WEB_CONTEXT_RESULTS,
    web_context_char_cap: int = WEB_CONTEXT_CHAR_CAP,
    web_queries: list[str] = None,
    web_reranker=None,
    reranker_query: str = None,
    filter_entity: str = "",
    reranker_candidate_cap: int = 40,
) -> str:
    """为单个查询检索 RAG 上下文。"""
    if not image_search and not web_search:
        return ""

    rag_context = "<search results>"

    # 图像搜索结果
    if image_search:
        img_context = ""
        image_search_results = search_pipeline(image, k=NUM_IMG_SEARCH_RESULTS)

        print("========== IMAGE SEARCH RAW RESULTS ==========")
        for idx, result in enumerate(image_search_results, 1):
            print(f"[Result {idx}] score={result.get('score')}")
            entity_names = [
                entity.get("entity_name")
                for entity in result.get("entities", [])
            ]
            print("entities:", _safe_str(entity_names))
        print("==============================================")
        image_entity_candidates = _select_image_entity_candidates(
            image_search_results
        )

        if image_entity_candidates:
            img_context += (
                "The image search produced possible entity names. They are visual"
                " neighbors, not verified identifications, and may all be wrong. Use a"
                " name only when the image itself clearly supports it. These names do"
                " not establish any factual attributes. If you visually confirm an"
                " exact identity, you may use only general knowledge you are highly"
                " confident about. Never choose a candidate merely because it appears"
                " first. If the image and candidates do not support a concise factual"
                " answer, reply exactly: I don't know.\n\n"
            )
            for candidate in image_entity_candidates:
                img_context += (
                    f"Candidate {candidate['rank']}: {candidate['name']}"
                    f" (visual similarity: {candidate['score']:.3f};"
                    f" occurrences: {candidate['occurrences']})\n"
                )

        if img_context:
            rag_context += img_context
            rag_context += (
                "Treat the candidates only as hints for what to inspect in the image."
                " Ignore every candidate that is not visually confirmed.\n\n"
            )

    # 若已获得图像摘要，则进行网页搜索
    if web_search:
        web_context = ""
        search_query = query if not full_query else full_query
        queries = [value for value in (web_queries or [search_query]) if value]
        if include_original_web_query and query not in queries:
            queries.append(query)
        unique_queries = list(dict.fromkeys(queries))
        result_groups = [
            search_pipeline(value, k=NUM_WEB_SEARCH_RESULTS)
            for value in unique_queries
        ]
        search_results = _merge_many_search_results(result_groups)
        search_results = _filter_search_results(
            search_results, query, filter_entity
        )
        if rerank_web_results:
            search_results = _rerank_search_results(search_results, search_query)
        if web_reranker is not None:
            search_results = _rerank_search_results(
                search_results, reranker_query or search_query
            )[:reranker_candidate_cap]
            search_results = web_reranker.rank(
                reranker_query or search_query, search_results
            )

        if search_results:
            web_context += (
                "You are given snippets from web page search results based on this"
                f' question: "{query}". These page snippets may or may not contain'
                " relevant or truthful information about the question. Incorporate"
                " these information into your answer ONLY IF you are confident they"
                " address the question. Higher-ranked documents are more relevant."
                " Prefer evidence that directly names the identified image entity and"
                " answers the requested property. Do not describe the image or search"
                " results. Do not state a number unless it is supported by a relevant"
                " snippet. Disregard unrelated evidence.\n\n"
            )

            webpage_count = 0
            for i, result in enumerate(search_results):
                if webpage_count >= max_web_context_results:
                    break
                result = WebSearchResult(result)
                snippet = result.get("page_snippet", "")
                if snippet:
                    page_name = result.get("page_name", "")
                    if len(web_context) + len(snippet) < web_context_char_cap:
                        web_context += (
                            f"<DOC>\nWebpage ID: [{webpage_count+1}]\nTitle:"
                            f" {page_name}\nWeb content snippet: {snippet}\n</DOC>\n\n"
                        )
                        webpage_count += 1
                    else:
                        break
        if web_context:
            rag_context += web_context
            rag_context += (
                "Incorporate these web search results into your answer ONLY IF you are"
                " confident they contain relevant or truthful information about the"
                " question. Disregard them otherwise.\n\n"
            )
    rag_context += "</search results>"

    return rag_context
