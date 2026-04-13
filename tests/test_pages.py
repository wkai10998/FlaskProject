import unittest

from app import app


class PageRenderingTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_programs_guides_and_assistant_pages_render_key_navigation_and_content(self):
        home = self.client.get("/")
        programs = self.client.get("/programs")
        guides = self.client.get("/guide")
        assistant = self.client.get("/assistant")

        self.assertEqual(home.status_code, 200)
        self.assertIn("ToCU", home.get_data(as_text=True))
        self.assertIn("专业速查", home.get_data(as_text=True))
        self.assertIn("操作步骤", home.get_data(as_text=True))
        self.assertIn("智能助手", home.get_data(as_text=True))

        self.assertEqual(programs.status_code, 200)
        self.assertIn("专业速查", programs.get_data(as_text=True))

        self.assertEqual(guides.status_code, 200)
        self.assertIn("操作步骤", guides.get_data(as_text=True))
        self.assertIn("01", guides.get_data(as_text=True))

        self.assertEqual(assistant.status_code, 200)
        self.assertIn("智能助手", assistant.get_data(as_text=True))

    def test_homepage_uses_cover_style_message_without_timeline_overview(self):
        html = self.client.get("/").get_data(as_text=True)

        self.assertIn("ToCU", html)
        self.assertIn("快速比较项目方向、语言要求与截止日期。", html)
        self.assertIn("从 6 个阶段进入完整申请流程与具体步骤。", html)
        self.assertIn("针对推荐信、截止时间和网申动作随时提问。", html)
        self.assertNotIn("把港中文硕士申请的时间、材料与步骤讲清楚", html)
        self.assertNotIn("港中文硕士申请信息服务平台。把项目、步骤与即时答疑放在一个温和而清晰的界面里。", html)
        self.assertNotIn("进入阶段", html)
        self.assertNotIn("Stage 01", html)

    def test_guides_page_shows_six_stage_overview_and_resume_hint(self):
        self.client.set_cookie("last_stage", "docs")
        html = self.client.get("/guide").get_data(as_text=True)

        self.assertIn("申请前准备（2.1+2.2）", html)
        self.assertIn("网申阶段（2.3）", html)
        self.assertIn("申请材料寄送（2.4）", html)
        self.assertIn("申请积极信号（2.5）", html)
        self.assertIn("缴纳留位费（2.6）", html)
        self.assertIn("入学前准备（2.7）", html)
        self.assertIn("继续上次进度", html)

    def test_programs_page_keeps_lookup_behavior_with_directory_style_copy(self):
        html = self.client.get("/programs").get_data(as_text=True)

        self.assertIn("专业速查", html)
        self.assertIn("用于快速对比专业方向、语言要求和截止日期", html)
        self.assertIn("输入专业名、学院或方向关键词", html)

    def test_guide_detail_keeps_progress_controls_and_materials_sections(self):
        html = self.client.get("/guide/docs").get_data(as_text=True)

        self.assertIn("步骤导航", html)
        self.assertIn("如何推进本步骤", html)
        self.assertIn("材料清单", html)
        self.assertTrue("标记为已完成" in html or "已完成" in html)

    def test_assistant_and_login_pages_still_render_primary_labels(self):
        assistant_html = self.client.get("/assistant").get_data(as_text=True)
        login_html = self.client.get("/?open_login=1&auth_tab=login").get_data(as_text=True)

        self.assertIn("智能助手", assistant_html)
        self.assertIn("快速提问", assistant_html)
        self.assertIn("登录 / 注册", login_html)


if __name__ == "__main__":
    unittest.main()
