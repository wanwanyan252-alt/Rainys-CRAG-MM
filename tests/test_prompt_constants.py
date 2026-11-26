import unittest

from example_agents.prompt_constants import normalize_abstention_response


class PromptConstantsTests(unittest.TestCase):
    def test_abstention_explanation_is_normalized(self):
        response = "I don't know. The image does not provide that information."
        self.assertEqual(normalize_abstention_response(response), "I don't know.")

    def test_non_abstention_is_preserved(self):
        response = "  The vehicle seats five people.  "
        self.assertEqual(
            normalize_abstention_response(response),
            "The vehicle seats five people.",
        )

    def test_verbose_insufficient_information_is_normalized(self):
        response = "I don't have enough information to answer this question."
        self.assertEqual(normalize_abstention_response(response), "I don't know.")


if __name__ == "__main__":
    unittest.main()
