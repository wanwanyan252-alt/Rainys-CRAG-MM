import unittest

from tools.build_p5_training_data import (
    image_ref,
    select_evidence,
    split_for_session,
)


class P5TrainingDataTests(unittest.TestCase):
    def test_session_split_is_stable(self):
        first = split_for_session("fixed-session")
        self.assertIn(first, {"train", "dev"})
        self.assertEqual(first, split_for_session("fixed-session"))

    def test_image_ref_routes_each_development_slice(self):
        self.assertIn("slice50", image_ref(49, "049.jpg"))
        self.assertIn("slice100", image_ref(50, "050.jpg"))
        self.assertIn("slice200", image_ref(100, "100.jpg"))
        self.assertIn("full_blind_cloud", image_ref(200, "200.jpg"))

    def test_evidence_selection_requires_answer_overlap(self):
        selected, scores = select_evidence(
            [
                "The vehicle has a 337 mile electric range.",
                "This unrelated document discusses flowers.",
            ],
            "The vehicle has a 337 mile range.",
        )
        self.assertEqual(selected, [0])
        self.assertGreater(scores[0], scores[1])

    def test_evidence_selection_rejects_unrelated_documents(self):
        selected, _ = select_evidence(
            ["An unrelated page about architecture."],
            "The product contains 25 grams of sugar.",
        )
        self.assertEqual(selected, [])


if __name__ == "__main__":
    unittest.main()
