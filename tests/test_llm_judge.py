import unittest
from unittest.mock import patch

from evaluation.llm_judge import LLMJudge
from tools.judge_slice_results import preliminary_score


class LlmJudgeTests(unittest.TestCase):
    @patch("evaluation.llm_judge.OpenAI")
    def test_openai_compatible_base_url(self, openai_mock):
        judge = LLMJudge("secret", "deepseek-flash", "https://api.deepseek.com")
        openai_mock.assert_called_once_with(
            api_key="secret", base_url="https://api.deepseek.com"
        )
        self.assertEqual(
            judge.request_extra_body, {"thinking": {"type": "disabled"}}
        )

    def test_preliminary_scores(self):
        self.assertEqual(preliminary_score("I don't know.", "answer"), (0, "abstention"))
        self.assertEqual(preliminary_score("Answer", "answer"), (1, "exact_match"))
        self.assertEqual(preliminary_score("Maybe", "answer"), (None, "llm_judge"))


if __name__ == "__main__":
    unittest.main()
