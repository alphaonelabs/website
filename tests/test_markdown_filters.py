from django.test import TestCase

from web.templatetags.markdown_filters import markdownify_sanitized


class MarkdownFiltersSanitizationTests(TestCase):
    """
    Regression tests covering the sanitizer boundary around the markdownify_sanitized function.
    """

    def test_markdownify_sanitized_strips_scripts_and_dangerous_tags(self):
        """Ensure <script>, <iframe>, <embed>, <object> tags and dangerous attributes are stripped."""
        # Test script tag removal (note: bleach keeps text content by default)
        sanitized = markdownify_sanitized('<script>alert("XSS")</script>')
        self.assertNotIn("<script>", sanitized)
        self.assertIn('alert("XSS")', sanitized)

        # Test attribute removal (onerror, onload, onclick)
        sanitized_img = markdownify_sanitized('<img src="x" onerror="alert(1)" onload="alert(2)">')
        self.assertIn('src="x"', sanitized_img)
        self.assertNotIn("onerror", sanitized_img)
        self.assertNotIn("onload", sanitized_img)

        sanitized_p = markdownify_sanitized('<p onclick="alert(1)">Click me</p>')
        self.assertIn("Click me", sanitized_p)
        self.assertNotIn("onclick", sanitized_p)

        # Test dangerous tags that are not in SAFE_TAGS
        # Note: markdownify might wrap the result in <p> tags
        dangerous_payloads = [
            ('<iframe src="javascript:alert(1)"></iframe>', ""),
            ('<embed src="evil.swf">', ""),
            ('<object data="evil.swf"></object>', ""),
        ]
        for payload, expected in dangerous_payloads:
            sanitized = markdownify_sanitized(payload)
            self.assertNotIn("<iframe", sanitized)
            self.assertNotIn("<embed", sanitized)
            self.assertNotIn("<object", sanitized)

    def test_markdownify_sanitized_enforces_protocols(self):
        """Ensure only allowed protocols (http, https, mailto) are permitted."""
        test_cases = [
            ("[JS](javascript:alert(1))", "<a>JS</a>"),
            ("[Data](data:text/html,xss)", "<a>Data</a>"),
            ("[HTTP](http://example.com)", '<a href="http://example.com">HTTP</a>'),
            ("[HTTPS](https://example.com)", '<a href="https://example.com">HTTPS</a>'),
            ("[Mail](mailto:test@example.com)", '<a href="mailto:test@example.com">Mail</a>'),
        ]
        for markdown_input, expected_substring in test_cases:
            self.assertIn(expected_substring, markdownify_sanitized(markdown_input))

    def test_markdownify_sanitized_preserves_legitimate_markdown(self):
        """Ensure standard Markdown features are preserved and correctly rendered."""
        # Links and Images
        self.assertIn('<a href="http://example.com">Link</a>', markdownify_sanitized("[Link](http://example.com)"))

        # Images (attributes might be reordered)
        sanitized_img = markdownify_sanitized("![Alt](http://example.com/img.png)")
        self.assertIn('src="http://example.com/img.png"', sanitized_img)
        self.assertIn('alt="Alt"', sanitized_img)

        # Tables
        table_md = "| Head |\n| --- |\n| Cell |"
        rendered = markdownify_sanitized(table_md)
        self.assertIn("<table>", rendered)
        self.assertIn("<thead>", rendered)
        self.assertIn("<tbody>", rendered)
        self.assertIn("<td>Cell</td>", rendered)

        # Fenced Code Blocks
        code_md = "```python\nprint(1)\n```"
        rendered = markdownify_sanitized(code_md)
        self.assertIn('<pre><code class="language-python">', rendered)
        self.assertIn("print(1)", rendered)

        # Blockquotes and Headings
        self.assertIn("<blockquote>", markdownify_sanitized("> Quote"))
        self.assertIn("<h1>Title</h1>", markdownify_sanitized("# Title"))

    def test_markdownify_sanitized_handles_empty_input(self):
        """Ensure empty or None input returns an empty string."""
        self.assertEqual(markdownify_sanitized(""), "")
        self.assertEqual(markdownify_sanitized(None), "")

    def test_markdownify_sanitized_preview_flow(self):
        """
        Simulate the markdownify sanitized preview flow (AJAX-like).
        Ensures that even complex payloads passed directly to the function are sanitized.
        """
        complex_payload = "Check this [link](javascript:alert(1)) and <script>console.log('x')</script>."
        sanitized = markdownify_sanitized(complex_payload)
        self.assertIn("<a>link</a>", sanitized)
        self.assertNotIn("<script>", sanitized)
        self.assertNotIn("javascript:", sanitized)
        self.assertIn("console.log('x')", sanitized)


if __name__ == "__main__":
    import unittest

    unittest.main()
