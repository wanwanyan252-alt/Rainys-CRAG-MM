import unittest

from example_agents.rule_agent import IDK, RuleAgent


def entity_context(name: str, score: float, attributes: str) -> str:
    return (
        "<search results>\n"
        f"Entity 1: {name} (retrieval score: {score:.3f})\n"
        f"Entity attributes: {attributes}\n\n"
        "Incorporate these image entity information into your answer ONLY IF "
        "you are confident they refer to the exact same entity.\n"
        "</search results>"
    )


class RuleAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = RuleAgent()

    def answer(self, query: str, context: str) -> str:
        return self.agent.batch_generate_response(
            queries=[query],
            images=[None],
            message_histories=[[]],
            rag_context_list=[context],
        )[0]

    def test_rejects_low_confidence_evidence(self):
        context = entity_context(
            "Example Minivan", 0.59, '{"seating_capacity": "7"}'
        )
        self.assertEqual(
            self.answer("Can it transport seven passengers?", context), IDK
        )

    def test_answers_seven_passenger_question_from_capacity(self):
        context = entity_context(
            "Example Minivan", 0.75, '{"seating_capacity": "7"}'
        )
        self.assertTrue(
            self.answer("Can it transport seven passengers?", context).startswith(
                "Yes"
            )
        )

    def test_answers_known_five_seat_vehicle_conservatively(self):
        context = entity_context(
            "Subaru WRX", 0.75, '{"body_style": "compact car"}'
        )
        self.assertTrue(
            self.answer("Can it transport seven passengers?", context).startswith(
                "No"
            )
        )

    def test_unknown_question_is_not_guessed(self):
        context = entity_context(
            "Subaru WRX", 0.75, '{"body_style": "compact car"}'
        )
        self.assertEqual(self.answer("What is its fuel economy?", context), IDK)


if __name__ == "__main__":
    unittest.main()
