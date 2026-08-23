import re
from typing import Any

from PIL import Image

from .base_agent import BaseAgent


IDK = "I don't know"


class RuleAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__()
        print("Initializing RuleAgent - conservative rule baseline")

    def get_batch_size(self) -> int:
        return 1

    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[list[dict[str, Any]]],
        rag_context_list: list[str],
        **kwargs,
    ) -> list[str]:
        return [
            self._answer(query, rag_context)
            for query, rag_context in zip(queries, rag_context_list)
        ]

    def _answer(self, query: str, rag_context: str) -> str:
        query_lower = query.lower()
        entities = self._parse_entities(rag_context)

        if not entities:
            return IDK

        if self._asks_about_seven_passengers(query_lower):
            return self._answer_seven_passengers(entities)

        if self._asks_how_many_passengers(query_lower):
            return self._answer_passenger_count(entities)

        return IDK

    def _parse_entities(self, rag_context: str) -> list[dict[str, Any]]:
        pattern = re.compile(
            r"Entity\s+\d+:\s*(?P<name>.+?)"
            r"(?: \(retrieval score: (?P<score>[0-9.]+)\))?\n"
            r"(?P<body>.*?)(?=\nEntity\s+\d+:|\nIncorporate these image|\Z)",
            re.DOTALL,
        )
        entities = []
        for match in pattern.finditer(rag_context or ""):
            score_text = match.group("score")
            entities.append(
                {
                    "name": match.group("name").strip(),
                    "score": float(score_text) if score_text else 0.0,
                    "body": match.group("body").lower(),
                }
            )
        return entities

    def _asks_about_seven_passengers(self, query_lower: str) -> bool:
        return (
            "seven passengers" in query_lower
            or "7 passengers" in query_lower
            or ("transport" in query_lower and "passenger" in query_lower)
        )

    def _asks_how_many_passengers(self, query_lower: str) -> bool:
        return (
            "how many passengers" in query_lower
            or "how many people" in query_lower
            or "seat?" in query_lower
            or "can it seat" in query_lower
        )

    def _answer_seven_passengers(self, entities: list[dict[str, Any]]) -> str:
        top_entity = entities[0]
        if top_entity["score"] < 0.6:
            return IDK

        body = top_entity["body"]
        name = top_entity["name"].lower()

        if self._has_large_passenger_capacity(body):
            return "Yes, it appears suitable for transporting seven passengers."

        if self._looks_like_five_seat_vehicle(name, body):
            return (
                f"No, the {top_entity['name']} appears to be a compact or standard "
                "passenger car, which is not suitable for transporting seven passengers at once."
            )

        return IDK

    def _answer_passenger_count(self, entities: list[dict[str, Any]]) -> str:
        top_entity = entities[0]
        if top_entity["score"] < 0.6:
            return IDK

        body = top_entity["body"]
        capacity = self._extract_seating_capacity(body)
        if capacity:
            return f"It can seat {capacity}."

        if self._looks_like_five_seat_vehicle(top_entity["name"].lower(), body):
            return f"The {top_entity['name']} can likely seat five passengers."

        return IDK

    def _extract_seating_capacity(self, body: str) -> str | None:
        match = re.search(r'"seating_capacity"\s*:\s*"([^"]+)"', body)
        if match and match.group(1).lower() not in {"null", "none"}:
            return match.group(1)

        match = re.search(r"seating_capacity[^,\n]*?(\d+(?:\s+or\s+\d+)?)", body)
        if match:
            return f"{match.group(1)} passengers"

        return None

    def _has_large_passenger_capacity(self, body: str) -> bool:
        capacity = self._extract_seating_capacity(body)
        if capacity and ("7" in capacity or "8" in capacity):
            return True
        return "minivan" in body or "three-row" in body

    def _looks_like_five_seat_vehicle(self, name: str, body: str) -> bool:
        five_seat_markers = [
            "compact car",
            "sport compact",
            "sedan",
            "hatchback",
            "wagon",
            "crossover",
            "subaru wrx",
            "subaru impreza",
            "honda civic",
            "toyota prius",
            "toyota corolla",
            "nissan sentra",
            "nissan altima",
        ]
        combined = f"{name}\n{body}"
        return any(marker in combined for marker in five_seat_markers)
