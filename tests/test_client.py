from __future__ import annotations

import unittest

from hw1_client import ReviewSession
from src.model_client import CompletionResult


class FakeClient:
    def complete(self, messages, tools=None):
        return CompletionResult("- OK: Test response", 10, 4, "fake", 1)


class ReviewSessionTests(unittest.TestCase):
    def test_stats_does_not_mutate_history_or_totals(self) -> None:
        session = ReviewSession(FakeClient(), "Use bullets.")
        session.submit("Review this.")
        history_before = list(session.history)
        totals_before = (session.stats.turns, session.stats.input_tokens, session.stats.output_tokens)
        first = session.stats_snapshot()
        second = session.stats_snapshot()
        self.assertEqual(first, second)
        self.assertEqual(session.history, history_before)
        self.assertEqual(
            (session.stats.turns, session.stats.input_tokens, session.stats.output_tokens),
            totals_before,
        )


if __name__ == "__main__":
    unittest.main()

