import pytest

from ingestion.converter import email_body_to_markdown, html_to_markdown


class TestHtmlToMarkdown:
    def test_simple_html(self) -> None:
        html = "<p>Hello <strong>world</strong></p>"
        result = html_to_markdown(html)
        assert "Hello" in result
        assert "**world**" in result

    def test_removes_script_tags(self) -> None:
        html = "<p>Content</p><script>alert('xss')</script>"
        result = html_to_markdown(html)
        assert "alert" not in result
        assert "Content" in result

    def test_removes_style_tags(self) -> None:
        html = "<style>body{color:red}</style><p>Visible</p>"
        result = html_to_markdown(html)
        assert "color:red" not in result
        assert "Visible" in result

    def test_heading_conversion(self) -> None:
        html = "<h1>Title</h1><h2>Subtitle</h2><p>Body</p>"
        result = html_to_markdown(html)
        assert "# Title" in result
        assert "## Subtitle" in result

    def test_link_conversion(self) -> None:
        html = '<p>Click <a href="https://example.com">here</a></p>'
        result = html_to_markdown(html)
        assert "[here](https://example.com)" in result

    def test_list_conversion(self) -> None:
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = html_to_markdown(html)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_empty_html(self) -> None:
        assert html_to_markdown("") == ""
        assert html_to_markdown("   ") == ""

    def test_excessive_whitespace_cleaned(self) -> None:
        html = "<p>Line 1</p>\n\n\n\n\n<p>Line 2</p>"
        result = html_to_markdown(html)
        assert "\n\n\n" not in result


class TestEmailBodyToMarkdown:
    def test_prefers_html(self) -> None:
        result = email_body_to_markdown("<p><strong>HTML</strong></p>", "Plain text")
        assert "**HTML**" in result

    def test_falls_back_to_text(self) -> None:
        result = email_body_to_markdown("", "Plain text body")
        assert result == "Plain text body"

    def test_falls_back_to_text_whitespace_html(self) -> None:
        result = email_body_to_markdown("   ", "Plain text body")
        assert result == "Plain text body"

    def test_both_empty(self) -> None:
        result = email_body_to_markdown("", "")
        assert result == ""
