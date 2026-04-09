import unittest

from app import app


class CourseStructureTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_core_pages_exist(self):
        for path in ["/", "/programs", "/guide", "/faq", "/assistant"]:
            response = self.client.get(path)
            self.assertEqual(
                response.status_code,
                200,
                msg=f"expected {path} to return 200, got {response.status_code}",
            )

    def test_guide_stage_page_exists(self):
        response = self.client.get("/guide/prep")
        self.assertEqual(response.status_code, 200)
        self.assertIn("步骤导航", response.get_data(as_text=True))

    def test_toggle_step_complete_api(self):
        response = self.client.post("/guide/prep/step/1/complete")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["step_key"], "prep:1")
        self.assertIn("completed_count", payload)


if __name__ == "__main__":
    unittest.main()
