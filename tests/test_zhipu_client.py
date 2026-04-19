import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from utils import zhipu_client


class ZhipuClientTestCase(unittest.TestCase):
    @staticmethod
    def _chat_response(content: str) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    @staticmethod
    def _embedding_response(vectors: list[list[float]]) -> SimpleNamespace:
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=vector) for vector in vectors]
        )

    def test_generate_answer_uses_sdk_chat_completions(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = self._chat_response("ok")

        with (
            patch.dict(
                os.environ,
                {
                    "ZHIPU_API_KEY": "test-key",
                    "ZHIPU_API_BASE": "https://example.com",
                    "ZHIPU_CHAT_MODEL": "GLM-4.5-AirX",
                    "ZHIPU_CHAT_MAX_TOKENS": "256",
                    "ZHIPU_CHAT_RETRIES": "2",
                },
                clear=False,
            ),
            patch.object(zhipu_client, "ZhipuAiClient", create=True) as mock_client_cls,
        ):
            mock_client_cls.return_value = fake_client
            answer = zhipu_client.generate_answer("sys", "user", temperature=0.6)

        self.assertEqual(answer, "ok")
        mock_client_cls.assert_called_once()
        client_kwargs = mock_client_cls.call_args.kwargs
        self.assertEqual(client_kwargs.get("api_key"), "test-key")
        self.assertEqual(client_kwargs.get("base_url"), "https://example.com")
        self.assertEqual(client_kwargs.get("max_retries"), 2)

        fake_client.chat.completions.create.assert_called_once_with(
            model="GLM-4.5-AirX",
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ],
            temperature=0.6,
            max_tokens=256,
        )

    def test_create_embeddings_uses_sdk_embeddings_api(self):
        fake_client = MagicMock()
        fake_client.embeddings.create.return_value = self._embedding_response(
            [[0.1, 0.2], [0.3, 0.4]]
        )

        with (
            patch.dict(
                os.environ,
                {
                    "ZHIPU_API_KEY": "test-key",
                    "ZHIPU_API_BASE": "https://example.com",
                    "ZHIPU_EMBEDDING_MODEL": "embedding-3",
                },
                clear=False,
            ),
            patch.object(zhipu_client, "ZhipuAiClient", create=True) as mock_client_cls,
        ):
            mock_client_cls.return_value = fake_client
            vectors = zhipu_client.create_embeddings(["first", "second"], dimensions=1024)

        self.assertEqual(vectors, [[0.1, 0.2], [0.3, 0.4]])
        mock_client_cls.assert_called_once()
        fake_client.embeddings.create.assert_called_once_with(
            model="embedding-3",
            input=["first", "second"],
            dimensions=1024,
        )

    def test_generate_answer_requires_sdk_dependency_when_missing(self):
        with (
            patch.dict(os.environ, {"ZHIPU_API_KEY": "test-key"}, clear=False),
            patch.object(zhipu_client, "ZhipuAiClient", None, create=True),
        ):
            with self.assertRaises(RuntimeError) as context:
                zhipu_client.generate_answer("sys", "user")

        self.assertIn("zai-sdk", str(context.exception))


if __name__ == "__main__":
    unittest.main()
