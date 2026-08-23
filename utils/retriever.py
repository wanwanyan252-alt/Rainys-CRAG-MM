# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import json
import sys

from utils.crag_web_result_fetcher import WebSearchResult
from cragmm_search.search import UnifiedSearchPipeline
from PIL import Image

NUM_IMG_SEARCH_RESULTS = 30
IMG_TOKEN_CAP = int(2000 * 4)  # 4 为“字符数 -> token 数”的换算乘数

NUM_WEB_SEARCH_RESULTS = 50
WEB_TOKEN_CAP = int(8000 * 4)  # 1.5 为“字符数 -> token 数”的换算乘数
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.6


def _safe_str(value):
    encoding = sys.stdout.encoding or "utf-8"
    return str(value).encode(encoding, errors="replace").decode(encoding)


def get_rag_context(
    query: str,
    image: Image.Image,
    search_pipeline: UnifiedSearchPipeline,
    image_search: bool,
    web_search: bool,
    full_query: str = None,
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
        image_search_results = [
            image_search_result
            for image_search_result in image_search_results
            if image_search_result.get("score", 0) > IMG_SEARCH_CONFIDENCE_THRESHOLD
        ]

        if len(image_search_results) > 0:
            img_context += (
                "You are given some image entity description retrieved based on visual"
                " similarity to the provided image. These may or may not represent the"
                " same entity in the provided image. Incorporate their information into"
                " your answer ONLY IF you are confident they refer to the exact same"
                " entity. Disregard them otherwise.\n\n"
            )

            entity_names = []
            for image_search_result in image_search_results:
                entities = image_search_result.get("entities", [])
                for entity in entities:
                    entity_name = entity["entity_name"]
                    if entity_name in entity_names:
                        continue
                    entity_names.append(entity_name)

            entity_names_str = ", ".join(entity_names)
            img_context += (
                "Here is a list of entity names retrieved based on visual similarity"
                f" to the provided image: {entity_names_str}.\n\n"
            )

            img_context += (
                "Here are some additional attributes for some of the entities. Only"
                " incoperate these information into your answer ONLY IF you are"
                " confidentthe referenced entity is in the provided image.\n"
            )
            entity_count = 0
            seen_entity = set()

            for image_search_result in image_search_results:
                if len(img_context) > IMG_TOKEN_CAP:
                    break

                retrieval_score = image_search_result.get("score", None)
                retrieval_score_text = ""
                if retrieval_score is not None:
                    retrieval_score_text = f" (retrieval score: {retrieval_score:.3f})"

                entities = image_search_result.get("entities", [])

                for entity in entities:
                    entity_name = entity["entity_name"]
                    if entity_name in seen_entity:
                        continue
                    seen_entity.add(entity_name)

                    if not entity.get("entity_attributes"):
                        continue

                    if (
                        len(img_context) + len(str(entity["entity_attributes"]))
                    ) < IMG_TOKEN_CAP:
                        img_context += (
                            f"Entity {entity_count+1}: {entity_name}"
                            f"{retrieval_score_text}\n"
                        )
                        try:
                            entity_attributes = json.dumps(
                                entity["entity_attributes"],
                                indent=2,
                                ensure_ascii=False,
                            )
                            img_context += f"Entity attributes: {entity_attributes}\n\n"
                        except Exception:
                            img_context += (
                                "Entity attributes:"
                                f" {str(entity['entity_attributes'])}\n\n"
                            )
                        entity_count += 1

        if img_context:
            rag_context += img_context
            rag_context += (
                "Incorporate these image entity information into your answer ONLY IF"
                " you are confident they refer to the exact same entity. Disregard them"
                " otherwise.\n\n"
            )

    # 若已获得图像摘要，则进行网页搜索
    if web_search:
        web_context = ""
        search_query = query if not full_query else full_query
        search_results = search_pipeline(search_query, k=NUM_WEB_SEARCH_RESULTS)

        if search_results:
            web_context += (
                "You are given snippets from web page search results based on this"
                f' question: "{query}". These page snippets may or may not contain'
                " relevant or truthful information about the question. Incorporate"
                " these information into your answer ONLY IF you are confident they"
                " address the question. Disregard them otherwise.\n\n"
            )

            webpage_count = 0
            for i, result in enumerate(search_results):
                result = WebSearchResult(result)
                snippet = result.get("page_snippet", "")
                if snippet:
                    page_name = result.get("page_name", "")
                    if len(web_context) + len(snippet) < WEB_TOKEN_CAP:
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
