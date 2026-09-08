from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[dict[str, str | None]] = []
        self.options: list[dict[str, str | None]] = []
        self.scripts: list[str | None] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"input", "textarea", "select"}:
            self.inputs.append({"tag": tag, **values})
        elif tag == "option":
            self.options.append(values)
        elif tag == "script":
            self.scripts.append(values.get("src"))

    def handle_data(self, data):
        self.text.append(data)


class WebRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = Path("index.html").read_text(encoding="utf-8")
        cls.js = Path("app.js").read_text(encoding="utf-8")
        cls.parser = FormParser()
        cls.parser.feed(cls.html)

    def test_title_and_domain_heading(self) -> None:
        self.assertIn("<title>DATA 260 Grocery Recall Manager</title>", self.html)
        self.assertIn("<h1>Grocery Recall Manager</h1>", self.html)

    def test_required_controls(self) -> None:
        by_id = {item.get("id"): item for item in self.parser.inputs}
        for field in ("productName", "brandName", "submitterEmail", "recallDetails", "category"):
            self.assertIn(field, by_id)
            self.assertIn("required", by_id[field])
        self.assertIn("autofocus", by_id["productName"])
        self.assertEqual(by_id["submitterEmail"].get("type"), "email")
        self.assertEqual(by_id["termsAccepted"].get("type"), "checkbox")

    def test_four_categories_and_exact_terms_label(self) -> None:
        category_values = [option.get("value") for option in self.parser.options if option.get("value")]
        self.assertEqual(len(category_values), 4)
        text = " ".join(" ".join(self.parser.text).split())
        self.assertIn("I agree to the terms and conditions.", text)

    def test_script_is_last_content_before_body_close(self) -> None:
        self.assertEqual(self.parser.scripts, ["/static/app.js"])
        self.assertRegex(self.html, r'<script src="/static/app\.js"></script>\s*</body>')

    def test_javascript_features(self) -> None:
        self.assertIn('const API_URL = "/api/recalls"', self.js)
        self.assertIn("payload.recallDetails.length <= 25", self.js)
        self.assertIn("!payload.termsAccepted", self.js)
        self.assertIn("JSON.stringify", self.js)
        self.assertIn('method: updating ? "PUT" : "POST"', self.js)
        self.assertIn('method: "DELETE"', self.js)
        self.assertIn("encodeURIComponent(query)", self.js)

    def test_visible_list_states_and_responsive_css(self) -> None:
        for state_id in ("loadingState", "emptyState", "errorState"):
            self.assertIn(f'id="{state_id}"', self.html)
        css = Path("styles.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 600px)", css)


if __name__ == "__main__":
    unittest.main()
