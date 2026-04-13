import re
import unittest

from app import app
from utils.content_loader import get_stages


class CourseStructureTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_core_pages_exist(self):
        for path in ["/", "/programs", "/guide", "/assistant"]:
            response = self.client.get(path)
            self.assertEqual(
                response.status_code,
                200,
                msg=f"expected {path} to return 200, got {response.status_code}",
            )

    def test_faq_routes_render_secondary_support_pages(self):
        list_response = self.client.get("/faq")
        detail_response = self.client.get("/faq/1")
        missing_response = self.client.get("/faq/some-legacy-path")

        self.assertEqual(list_response.status_code, 200)
        self.assertIn("常见问题", list_response.get_data(as_text=True))

        self.assertEqual(detail_response.status_code, 200)
        self.assertIn("评论区", detail_response.get_data(as_text=True))

        self.assertEqual(missing_response.status_code, 404)

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

    def test_header_tab_order_matches_page_mapping(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        nav_match = re.search(
            r'<nav class="tocu-site-nav"[^>]*>(.*?)</nav>',
            html,
            re.S,
        )
        self.assertIsNotNone(nav_match, msg="desktop navigation block should exist")
        nav_html = nav_match.group(1)

        expected_order = ["首页", "专业速查", "操作步骤", "智能助手"]
        last_index = -1
        for label in expected_order:
            current_index = nav_html.find(f">{label}</a>")
            self.assertNotEqual(
                current_index,
                -1,
                msg=f"navigation should contain tab label: {label}",
            )
            self.assertGreater(
                current_index,
                last_index,
                msg=f"tab order is incorrect around label: {label}",
            )
            last_index = current_index

        self.assertNotIn(">问题清单</a>", nav_html)
        self.assertNotIn(">文件清单</a>", nav_html)

    def test_homepage_uses_cover_layout_and_moves_process_overview_to_guides(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("tocu-home-cover__title", html)
        self.assertIn("快速比较项目方向、语言要求与截止日期。", html)
        self.assertNotIn("tocu-roadmap-arrows", html)
        self.assertNotIn("tocu-roadmap-card-", html)

        guide_html = self.client.get("/guide").get_data(as_text=True)
        actual_count = guide_html.count('<article class="tocu-stage-card')
        self.assertEqual(actual_count, len(get_stages()))


if __name__ == "__main__":
    unittest.main()
