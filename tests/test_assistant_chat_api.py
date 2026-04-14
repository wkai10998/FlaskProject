import unittest
from unittest.mock import patch

import app as app_module


class AssistantChatApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_assistant_page_renders_chat_shell(self):
        response = self.client.get("/assistant")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-assistant-shell', html)
        self.assertIn('data-assistant-stage="empty"', html)
        self.assertIn('data-assistant-empty-state', html)
        self.assertIn('id="assistant-chat-log"', html)
        self.assertIn('id="assistant-chat-form"', html)
        self.assertIn('data-assistant-compose-fixed', html)
        self.assertIn("/assistant/message", html)

    def test_assistant_message_api_success(self):
        with patch.object(
            app_module,
            "ask_assistant",
            return_value=("建议提前 4-8 周联系老师。", [{"source": "官方知识库", "link": "/assistant"}]),
        ):
            response = self.client.post("/assistant/message", json={"message": "推荐信要提前多久联系老师？"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertIn("answer", payload)
        self.assertIn("sources", payload)
        self.assertIn("elapsed_ms", payload)

    def test_assistant_message_api_rejects_short_message(self):
        response = self.client.post("/assistant/message", json={"message": "a"})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
