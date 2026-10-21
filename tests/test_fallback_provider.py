import unittest
from unittest.mock import MagicMock
from core.llm_agent import LLMAgent

class TestFallbackProvider(unittest.TestCase):

    def test_automatic_failover_to_secondary_provider(self):
        # Configure two mock providers
        providers = [
            {
                "name": "primary_provider",
                "api_key": "dummy_key_1",
                "model": "model_1",
                "base_url": "https://api.mock1.com/v1",
                "enabled": True
            },
            {
                "name": "secondary_provider",
                "api_key": "dummy_key_2",
                "model": "model_2",
                "base_url": "https://api.mock2.com/v1",
                "enabled": True
            }
        ]

        agent = LLMAgent(providers=providers)

        # Mock client 1 to throw a RateLimitError (e.g. 429)
        mock_client_1 = MagicMock()
        mock_client_1.chat.completions.create.side_effect = Exception("429 Rate limit reached on primary provider")

        # Mock client 2 to succeed
        mock_choice = MagicMock()
        mock_choice.message.content = "Secondary provider handled this successfully."
        mock_choice.message.tool_calls = None
        mock_response_2 = MagicMock()
        mock_response_2.choices = [mock_choice]

        mock_client_2 = MagicMock()
        mock_client_2.chat.completions.create.return_value = mock_response_2

        # Inject mock clients
        agent.active_clients[0]["client"] = mock_client_1
        agent.active_clients[1]["client"] = mock_client_2

        # Process query
        result = agent.process_query("What is the weather today?")

        # Assert failover occurred seamlessly
        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "secondary_provider")
        self.assertEqual(result["text"], "Secondary provider handled this successfully.")

        # Verify that primary was tried first and secondary was called upon failure
        mock_client_1.chat.completions.create.assert_called_once()
        mock_client_2.chat.completions.create.assert_called_once()

if __name__ == "__main__":
    unittest.main()
