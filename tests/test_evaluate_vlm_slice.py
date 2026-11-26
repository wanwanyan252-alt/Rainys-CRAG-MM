import json
from pathlib import Path
import tempfile
import unittest

from tools.evaluate_vlm_slice import (
    build_baseline_entity_extraction_prompt,
    build_entity_extraction_prompt,
    build_entity_views,
    build_multicrop_selection_prompt,
    build_web_search_query,
    build_multi_web_queries,
    classify_question_route,
    build_focused_web_search_query,
    build_grounded_retry_prompt,
    response_needs_completeness_retry,
    build_web_entity_fallback_prompt,
    extract_tagged_entity,
    gate_entity_with_image_candidates,
    is_abstention,
    first_value,
    load_manifest,
    parse_positions,
    ocr_supports_entity,
    token_f1,
    should_run_multicrop_fallback,
    validate_multicrop_entity,
    entity_candidate_was_observed,
    choose_uncontested_baseline_candidate,
    choose_only_observed_candidate,
    canonicalize_entity_spelling,
    chart_category_answer,
    extract_query_scope_terms,
    normalize_numeric_text,
    numeric_context_tokens,
    minimize_boolean_answer,
    minimize_versus_answer,
    validate_numeric_evidence,
    truncate_answer_tokens,
)


class EvaluateVlmSliceTests(unittest.TestCase):
    def test_truncate_answer_tokens_uses_tokenizer_limit(self):
        class Tokenizer:
            def encode(self, text, add_special_tokens=False):
                return text.split()

            def decode(self, ids, skip_special_tokens=True):
                return " ".join(ids)

        self.assertEqual(
            truncate_answer_tokens("one two three four", Tokenizer(), 3),
            "one two three",
        )

    def test_question_router_separates_comparison_ocr_and_lookup(self):
        self.assertEqual(
            classify_question_route("Is this cheaper than the other model?"),
            "comparison",
        )
        self.assertEqual(
            classify_question_route("How much sugar is on this label?"),
            "ocr",
        )
        self.assertEqual(
            classify_question_route("When was this logo introduced?"),
            "ocr",
        )

    def test_ocr_can_support_multi_token_entity(self):
        self.assertTrue(
            ocr_supports_entity("Simply Lemonade", "SIMPLY LEMONADE raspberry")
        )
        self.assertFalse(ocr_supports_entity("Tesla Model Y", "MODEL 3"))

    def test_load_manifest_limit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "manifest.json"
            path.write_text(json.dumps([{"index": 0}, {"index": 1}]), encoding="utf-8")
            self.assertEqual(load_manifest(path, 1), [{"index": 0}])

    def test_manifest_dataset_index_can_preserve_global_position(self):
        entries = [{"index": 50}, {"index": 51}]
        selected = list(enumerate(entries))
        positions = [entry.get("index", manifest_position) for manifest_position, entry in selected]
        self.assertEqual(positions, [50, 51])

    def test_first_value(self):
        entry = {"turns": {"query": ["question"]}}
        self.assertEqual(first_value(entry, "turns", "query"), "question")

    def test_parse_positions_preserves_requested_order(self):
        self.assertEqual(parse_positions("7, 0,16", 50), [7, 0, 16])
        self.assertIsNone(parse_positions(None, 50))

    def test_parse_positions_rejects_duplicates_and_out_of_range(self):
        with self.assertRaises(SystemExit):
            parse_positions("1,1", 50)
        with self.assertRaises(SystemExit):
            parse_positions("50", 50)

    def test_build_web_search_query_uses_identified_entity(self):
        query = build_web_search_query("How many seats?", "Subaru WRX")
        self.assertIn("Subaru WRX", query)
        self.assertIn("How many seats?", query)

    def test_focused_web_query_keeps_entity_and_requested_property(self):
        query = build_focused_web_search_query(
            "When was the artist who made this born?", "Andrea della Robbia"
        )
        self.assertEqual(query, "Andrea della Robbia artist born")
        vehicle_query = build_focused_web_search_query(
            "What is the towing capacity and torque for the 2024 version?",
            "RAM 3500",
        )
        self.assertIn("towing", vehicle_query)
        self.assertIn("torque", vehicle_query)
        self.assertIn("2024", vehicle_query)

    def test_multi_web_queries_include_original_entity_and_ocr(self):
        queries = build_multi_web_queries(
            "How much sugar does this have?",
            "Simply Lemonade",
            "SIMPLY LEMONADE 25g sugar",
            "ocr",
        )
        self.assertGreaterEqual(len(queries), 3)
        self.assertEqual(queries[0], "How much sugar does this have?")
        self.assertTrue(any("Simply Lemonade" in value for value in queries))
        self.assertTrue(any("25g" in value for value in queries))

    def test_build_web_search_query_ignores_abstention(self):
        self.assertEqual(
            build_web_search_query("How many seats?", "UNKNOWN"),
            "How many seats?",
        )

    def test_grounded_retry_prompt_allows_only_simple_evidence_operations(self):
        prompt = build_grounded_retry_prompt(
            "Can it travel 40 miles on 5 gallons?", "Chevrolet Trailblazer"
        )
        self.assertIn("simple arithmetic", prompt)
        self.assertIn("year-order comparisons", prompt)
        self.assertIn("Chevrolet Trailblazer", prompt)

    def test_species_answer_retries_when_only_umbrella_name_is_given(self):
        query = "Which species of this flower are used for infusions?"
        self.assertTrue(
            response_needs_completeness_retry(query, "The flower is chamomile.")
        )
        self.assertFalse(
            response_needs_completeness_retry(
                query, "German chamomile and Roman chamomile are used."
            )
        )

    def test_web_entity_fallback_requires_image_and_title_agreement(self):
        prompt = build_web_entity_fallback_prompt(
            "Can the tall tower withstand an earthquake?"
        )
        self.assertIn("web result titles", prompt)
        self.assertIn("image and at least one relevant title", prompt)

    def test_extract_tagged_entity(self):
        self.assertEqual(
            extract_tagged_entity("<entity>Subaru WRX</entity>"),
            "Subaru WRX",
        )
        self.assertEqual(extract_tagged_entity("<entity>UNKNOWN</entity>"), "")
        self.assertEqual(extract_tagged_entity("The answer is Subaru WRX."), "")

    def test_entity_extraction_prompt_targets_question_referent(self):
        prompt = build_entity_extraction_prompt("What can these machines clear?")
        self.assertIn("resolve the noun phrase", prompt)
        self.assertIn("foreground occluders", prompt)
        baseline = build_baseline_entity_extraction_prompt("What is this car?")
        self.assertIn("specific main object", baseline)

    def test_entity_views_cover_full_and_directional_crops(self):
        from PIL import Image

        views = build_entity_views(Image.new("RGB", (100, 200)))
        self.assertEqual(
            [name for name, _ in views],
            [
                "full",
                "lower",
                "left",
                "right",
                "lower_left",
                "lower_right",
                "lower_left_detail",
                "right_center_detail",
                "center",
            ],
        )
        self.assertEqual(dict(views)["lower"].size, (100, 140))
        self.assertEqual(dict(views)["left"].size, (65, 200))
        self.assertEqual(dict(views)["lower_right"].size, (65, 140))
        self.assertEqual(dict(views)["lower_left_detail"].size, (52, 124))
        self.assertEqual(dict(views)["right_center_detail"].size, (41, 84))
        self.assertEqual(dict(views)["center"].size, (70, 140))

    def test_multicrop_fallback_preserves_specific_baseline_entity(self):
        self.assertFalse(
            should_run_multicrop_fallback("What color are these fruits?", "avocado")
        )
        self.assertFalse(
            should_run_multicrop_fallback(
                "Which generation had highest sales?", "Honda HR-V"
            )
        )
        self.assertTrue(
            should_run_multicrop_fallback(
                "Which generation had highest sales?", "Honda"
            )
        )
        self.assertTrue(should_run_multicrop_fallback("Who designed this?", ""))

    def test_extract_query_scope_terms(self):
        self.assertEqual(
            extract_query_scope_terms("Which model sold most in Canada?"),
            ["canada"],
        )
        self.assertEqual(extract_query_scope_terms("What is in this image?"), [])
        self.assertIn("5 people", normalize_numeric_text("five people"))

    def test_numeric_evidence_requires_number_in_document(self):
        context = (
            "<search results><DOC>Title: Specs\nWeb content snippet: It seats five"
            " people.</DOC></search results>"
        )
        self.assertEqual(
            validate_numeric_evidence("How many seats?", "It seats 4 people.", context),
            (False, "unsupported_number:4"),
        )
        self.assertEqual(
            validate_numeric_evidence("How many seats?", "It seats 5 people.", context),
            (True, "supported"),
        )
        self.assertEqual(
            validate_numeric_evidence(
                "Can it carry seven people?",
                "No, it cannot carry seven people; it seats five.",
                context,
            ),
            (True, "supported"),
        )
        unrelated_number_context = (
            "<search results><DOC>Title: Specs\nWeb content snippet: It has"
            " 4-wheel drive and seats five people.</DOC></search results>"
        )
        self.assertEqual(
            validate_numeric_evidence(
                "Can it carry seven people?",
                "No, it has four seats.",
                unrelated_number_context,
            ),
            (False, "unsupported_number:4"),
        )

    def test_numeric_context_tokens_capture_local_property(self):
        contexts = numeric_context_tokens("It has four seats and AWD.", "4")
        self.assertIn("seat", contexts[0])

    def test_numeric_evidence_respects_query_scope(self):
        context = (
            "<search results>"
            "<DOC>Title: US sales\nWeb content snippet: US sales were 82,041.</DOC>"
            "<DOC>Title: Canada sales\nWeb content snippet: Canada sales were 14,149.</DOC>"
            "</search results>"
        )
        self.assertEqual(
            validate_numeric_evidence(
                "Which sold most in Canada?", "It sold 82,041.", context
            ),
            (False, "out_of_scope_number:82041"),
        )
        self.assertEqual(
            validate_numeric_evidence(
                "Which sold most in Canada?", "It sold 14,149.", context
            ),
            (True, "supported"),
        )

    def test_numeric_evidence_accepts_supported_year_without_property_word_match(self):
        context = (
            "<search results><DOC>Title: History\nWeb content snippet: The toys were"
            " created in 1985.</DOC></search results>"
        )
        self.assertEqual(
            validate_numeric_evidence(
                "When did these go on sale?", "They first went on sale in 1985.", context
            ),
            (True, "supported"),
        )

    def test_numeric_evidence_handles_decimal_without_treating_it_as_year(self):
        context = "<DOC>The engine displacement is 2.75 liters.</DOC>"
        self.assertEqual(
            validate_numeric_evidence(
                "What is the engine displacement?",
                "The engine displacement is 2.75 liters.",
                context,
            ),
            (True, "supported"),
        )

    def test_minimize_boolean_answer_removes_risky_explanation(self):
        self.assertEqual(
            minimize_boolean_answer(
                "Is this good for seven passengers?",
                "It is not good for seven passengers, as it has four seats.",
            ),
            "It is not good for seven passengers.",
        )
        self.assertEqual(
            minimize_boolean_answer(
                "Was it before Pluto?",
                "The date may be 1930. Therefore, Minnie appeared before Pluto.",
            ),
            "Minnie appeared before Pluto.",
        )
        self.assertEqual(
            minimize_boolean_answer(
                "Was this car around first?",
                "It appeared in 2016. The other car appeared in 1961, so this car was not around first.",
            ),
            "this car was not around first.",
        )
        self.assertEqual(
            minimize_boolean_answer(
                "Can it get from Washington, DC to Baltimore?",
                "It can get from Washington, D.C. to Baltimore, as it has enough fuel.",
            ),
            "It can get from Washington, D.C. to Baltimore.",
        )

    def test_minimize_versus_answer_keeps_first_year_per_side(self):
        response = (
            "Sylvanian Families first went on sale in 1985, while Hello Kitty first"
            " appeared in 1974 and was released in 1975."
        )
        self.assertEqual(
            minimize_versus_answer(
                "When did these go on sale versus Hello Kitty?", response
            ),
            "Sylvanian Families first went on sale in 1985 while Hello Kitty first appeared in 1974.",
        )
        self.assertEqual(
            minimize_versus_answer("What is this?", response), response
        )

    def test_multicrop_selection_prompt_deduplicates_candidates(self):
        prompt = build_multicrop_selection_prompt(
            "Which vehicle is this?",
            [
                {"entity": "Honda Pilot"},
                {"entity": "honda pilot"},
                {"entity": "Nissan Patrol"},
            ],
        )
        self.assertEqual(prompt.count("Honda Pilot"), 1)
        self.assertIn("Nissan Patrol", prompt)

    def test_multicrop_selection_prefers_visible_numeric_badge_for_specs(self):
        prompt = build_multicrop_selection_prompt(
            "What is the 2024 version towing capacity and engine torque?",
            [{"entity": "RAM 2500"}, {"entity": "RAM 3500"}],
        )
        self.assertIn("visible model badge", prompt)

    def test_multicrop_validation_accepts_repeated_entity(self):
        observations = [
            {"entity": "Honda Pilot", "image_context": ""},
            {"entity": "honda pilot", "image_context": ""},
        ]
        self.assertEqual(
            validate_multicrop_entity("Honda Pilot", observations), "Honda Pilot"
        )

    def test_multicrop_validation_rejects_unobserved_entity(self):
        observations = [{"entity": "Nissan Patrol", "image_context": ""}]
        self.assertEqual(
            validate_multicrop_entity("Honda Pilot", observations), ""
        )

    def test_search_candidate_must_come_from_a_crop_observation(self):
        observations = [
            {"entity": "2015 Chevrolet Suburban", "image_context": ""},
            {"entity": "Chevrolet Suburban", "image_context": ""},
        ]
        self.assertTrue(
            entity_candidate_was_observed(
                "2015 Chevrolet Suburban", observations
            )
        )
        self.assertFalse(
            entity_candidate_was_observed("Nissan Rogue", observations)
        )

    def test_uncontested_baseline_entity_can_be_used_for_search(self):
        observations = [
            {"entity": "Radio City Music Hall"},
            {"entity": ""},
            {"entity": ""},
        ]
        self.assertEqual(
            choose_uncontested_baseline_candidate(observations),
            "Radio City Music Hall",
        )
        observations.append({"entity": "Arsenal Stadium"})
        self.assertEqual(choose_uncontested_baseline_candidate(observations), "")

    def test_only_nonempty_crop_entity_can_be_used_for_search(self):
        observations = [
            {"entity": ""},
            {"entity": "SPACE NEEDLE"},
            {"entity": ""},
        ]
        self.assertEqual(
            choose_only_observed_candidate(observations), "SPACE NEEDLE"
        )
        observations.append({"entity": "CN Tower"})
        self.assertEqual(choose_only_observed_candidate(observations), "")

    def test_entity_spelling_uses_observed_singular_variant(self):
        observations = [
            {"entity": "Andrea della Robbia"},
            {"entity": "ANDREA DELLA ROBBIAS"},
        ]
        self.assertEqual(
            canonicalize_entity_spelling("ANDREA DELLA ROBBIAS", observations),
            "Andrea della Robbia",
        )

    def test_chart_category_answer_uses_age_and_sex_without_extra_numbers(self):
        self.assertEqual(
            chart_category_answer(
                "Which age and sex had the least falls?", "18-24 Males"
            ),
            "males aged 18-24.",
        )
        self.assertEqual(
            chart_category_answer(
                "Which age and sex had the least falls?", "18-24 Male"
            ),
            "males aged 18-24.",
        )
        self.assertEqual(chart_category_answer("Which car is this?", "18-24 Males"), "")

    def test_top_candidate_requires_repeated_support(self):
        weak = "Candidate 1: Carne asada fries (visual similarity: 0.725; occurrences: 2)"
        strong = "Candidate 1: Subaru WRX (visual similarity: 0.642; occurrences: 4)"
        lower = "Candidate 7: avocado (visual similarity: 0.776; occurrences: 1)"
        self.assertEqual(
            gate_entity_with_image_candidates("Carne asada fries", weak), ""
        )
        self.assertEqual(
            gate_entity_with_image_candidates("Subaru WRX", strong), "Subaru WRX"
        )
        self.assertEqual(
            gate_entity_with_image_candidates("avocado", lower), "avocado"
        )

    def test_proxy_metrics_helpers(self):
        self.assertTrue(is_abstention("I don't know."))
        self.assertFalse(is_abstention("No, it seats five."))
        self.assertEqual(token_f1("same words", "same words"), 1.0)
        self.assertEqual(token_f1("no overlap", "different tokens"), 0.0)


if __name__ == "__main__":
    unittest.main()
