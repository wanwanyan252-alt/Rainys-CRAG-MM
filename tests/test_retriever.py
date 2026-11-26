import unittest

from PIL import Image

from utils.retriever import (
    MAX_IMG_ENTITY_CANDIDATES,
    MAX_WEB_CONTEXT_RESULTS,
    _select_image_entity_candidates,
    _filter_search_results,
    _merge_many_search_results,
    _merge_search_results,
    _rerank_search_results,
    get_rag_context,
)


class FakeSearchPipeline:
    def __call__(self, value, k):
        if isinstance(value, Image.Image):
            return [
                {
                    "score": 0.75,
                    "entities": [
                        {
                            "entity_name": "Example Car",
                            "entity_attributes": {"seating_capacity": "5"},
                        }
                    ],
                },
                {
                    "score": 0.40,
                    "entities": [
                        {
                            "entity_name": "Low Confidence Car",
                            "entity_attributes": {"seating_capacity": "7"},
                        }
                    ],
                },
            ]
        return [
            {
                "page_name": "Example page",
                "page_snippet": "Useful web evidence.",
                "page_url": "https://example.test",
            }
        ]


class RetrieverTests(unittest.TestCase):
    def test_no_search_returns_empty_context(self):
        context = get_rag_context(
            query="question",
            image=Image.new("RGB", (1, 1)),
            search_pipeline=FakeSearchPipeline(),
            image_search=False,
            web_search=False,
        )
        self.assertEqual(context, "")

    def test_combined_context_filters_low_confidence_image_result(self):
        context = get_rag_context(
            query="question",
            image=Image.new("RGB", (1, 1)),
            search_pipeline=FakeSearchPipeline(),
            image_search=True,
            web_search=True,
        )
        self.assertIn(
            "Example Car (visual similarity: 0.750; occurrences: 1)", context
        )
        self.assertNotIn("Low Confidence Car", context)
        self.assertNotIn("seating_capacity", context)
        self.assertIn("Useful web evidence.", context)

    def test_web_context_result_count_is_capped(self):
        class ManyWebResultsPipeline:
            def __call__(self, value, k):
                return [
                    {
                        "page_name": f"Page {index}",
                        "page_snippet": f"Evidence {index}",
                        "page_url": f"https://example.test/{index}",
                    }
                    for index in range(MAX_WEB_CONTEXT_RESULTS + 5)
                ]

        context = get_rag_context(
            query="question",
            image=Image.new("RGB", (1, 1)),
            search_pipeline=ManyWebResultsPipeline(),
            image_search=False,
            web_search=True,
        )
        self.assertEqual(context.count("Webpage ID:"), MAX_WEB_CONTEXT_RESULTS)
        self.assertNotIn(f"Evidence {MAX_WEB_CONTEXT_RESULTS}", context)

    def test_image_candidates_are_deduplicated_and_capped(self):
        results = [
            {
                "score": 0.9 - index * 0.01,
                "entities": [{"entity_name": f"Entity {index}"}],
            }
            for index in range(MAX_IMG_ENTITY_CANDIDATES + 3)
        ]
        results.insert(
            1,
            {"score": 0.89, "entities": [{"entity_name": "Entity 0"}]},
        )
        candidates = _select_image_entity_candidates(results)
        self.assertEqual(len(candidates), MAX_IMG_ENTITY_CANDIDATES)
        self.assertEqual(candidates[0]["name"], "Entity 0")
        self.assertEqual(
            len({candidate["name"] for candidate in candidates}), len(candidates)
        )

    def test_merge_search_results_interleaves_and_deduplicates(self):
        primary = [
            {"page_url": "p1", "page_name": "Primary 1"},
            {"page_url": "shared", "page_name": "Shared"},
        ]
        secondary = [
            {"page_url": "s1", "page_name": "Secondary 1"},
            {"page_url": "shared", "page_name": "Shared duplicate"},
        ]
        merged = _merge_search_results(primary, secondary)
        self.assertEqual(
            [result["page_url"] for result in merged],
            ["p1", "s1", "shared"],
        )

    def test_merge_many_search_results_round_robins_and_deduplicates(self):
        merged = _merge_many_search_results(
            [
                [{"page_url": "a"}, {"page_url": "shared"}],
                [{"page_url": "b"}, {"page_url": "shared"}],
                [{"page_url": "c"}],
            ]
        )
        self.assertEqual([item["page_url"] for item in merged], ["a", "b", "c", "shared"])

    def test_entity_scope_filter_keeps_matching_market_documents(self):
        results = [
            {
                "page_name": f"Canada {index}",
                "page_snippet": "Honda HR-V Canada sales 2017",
            }
            for index in range(3)
        ] + [
            {
                "page_name": "US result",
                "page_snippet": "Honda HR-V United States sales 2017",
            }
        ]
        filtered = _filter_search_results(
            results, "Honda HR-V sales in Canada in 2017", "Honda HR-V"
        )
        self.assertEqual(len(filtered), 3)
        self.assertTrue(all("Canada" in item["page_name"] for item in filtered))

    def test_dual_web_query_includes_entity_and_original_results(self):
        class RecordingPipeline:
            def __init__(self):
                self.queries = []

            def __call__(self, value, k):
                self.queries.append(value)
                return [
                    {
                        "page_name": str(value),
                        "page_snippet": f"Evidence for {value}",
                        "page_url": f"https://example.test/{len(self.queries)}",
                    }
                ]

        pipeline = RecordingPipeline()
        context = get_rag_context(
            query="When versus Hello Kitty?",
            image=Image.new("RGB", (1, 1)),
            search_pipeline=pipeline,
            image_search=False,
            web_search=True,
            full_query="Identified image entity: Sylvanian Families.",
            include_original_web_query=True,
        )
        self.assertEqual(len(pipeline.queries), 2)
        self.assertIn("Evidence for Identified image entity", context)
        self.assertIn("Evidence for When versus Hello Kitty?", context)

    def test_rerank_search_results_promotes_rare_query_constraints(self):
        results = [
            {
                "page_name": "General sales",
                "page_snippet": "Honda HR-V sales in the United States",
            },
            {
                "page_name": "Canada sales",
                "page_snippet": "Honda HR-V annual sales in Canada in 2017",
            },
        ]
        reranked = _rerank_search_results(
            results, "Honda HR-V annual sales Canada 2017"
        )
        self.assertEqual(reranked[0]["page_name"], "Canada sales")

    def test_multi_query_uses_independent_reranker(self):
        class RecordingPipeline:
            def __init__(self):
                self.queries = []

            def __call__(self, value, k):
                self.queries.append(value)
                return [
                    {
                        "page_name": f"Page {value}",
                        "page_snippet": f"Evidence for {value}",
                        "page_url": f"https://example.test/{value}",
                    }
                ]

        class FakeReranker:
            def __init__(self):
                self.query = None

            def rank(self, query, results):
                self.query = query
                return list(reversed(results))

        pipeline = RecordingPipeline()
        reranker = FakeReranker()
        context = get_rag_context(
            query="question",
            image=Image.new("RGB", (1, 1)),
            search_pipeline=pipeline,
            image_search=False,
            web_search=True,
            web_queries=["query one", "query two", "query three"],
            web_reranker=reranker,
            reranker_query="rerank query",
        )
        self.assertEqual(pipeline.queries, ["query one", "query two", "query three"])
        self.assertEqual(reranker.query, "rerank query")
        self.assertIn("Evidence for query three", context)


if __name__ == "__main__":
    unittest.main()
