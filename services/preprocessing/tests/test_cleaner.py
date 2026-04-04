from preprocessing.cleaner import clean_email_text, prepare_embedding_text


class TestCleanEmailText:
    def test_plain_text(self):
        assert clean_email_text("Hello, how are you?") == "Hello, how are you?"

    def test_empty_input(self):
        assert clean_email_text("") == ""
        assert clean_email_text("   ") == ""

    def test_strips_standard_signature(self):
        text = "Main content here.\n\n-- \nJohn Doe\nSenior Engineer\njohn@example.com"
        result = clean_email_text(text)
        assert "Main content here." in result
        assert "John Doe" not in result

    def test_strips_iphone_signature(self):
        text = "Quick reply from phone.\n\nSent from my iPhone"
        result = clean_email_text(text)
        assert "Quick reply" in result
        assert "iPhone" not in result

    def test_strips_outlook_mobile_signature(self):
        text = "See attached.\n\nGet Outlook for iOS"
        result = clean_email_text(text)
        assert "See attached." in result
        assert "Outlook" not in result

    def test_strips_quoted_reply_angle_brackets(self):
        text = "My response.\n\n> Previous message\n> More quoted text"
        result = clean_email_text(text)
        assert "My response." in result
        assert "Previous message" not in result

    def test_strips_on_wrote_block(self):
        text = "I agree.\n\nOn Mon, Jan 1, 2026 at 10:00 AM Alice <alice@ex.com> wrote:"
        result = clean_email_text(text)
        assert "I agree." in result
        assert "Alice" not in result

    def test_strips_outlook_original_message(self):
        text = "Thanks.\n\n--- Original Message ---\nFrom: Bob\nContent here"
        result = clean_email_text(text)
        assert "Thanks." in result
        assert "Original Message" not in result

    def test_strips_outlook_header_block(self):
        text = "Noted.\n\nFrom: sender@example.com\nSent: Monday\nTo: me@example.com\nSubject: Re: Test"
        result = clean_email_text(text)
        assert "Noted." in result
        assert "sender@example.com" not in result

    def test_strips_disclaimer(self):
        text = "Here is the report.\n\nCONFIDENTIALITY NOTICE: This email is intended only for..."
        result = clean_email_text(text)
        assert "report" in result
        assert "CONFIDENTIALITY" not in result

    def test_collapses_excessive_newlines(self):
        text = "Line one.\n\n\n\n\nLine two."
        result = clean_email_text(text)
        assert result == "Line one.\n\nLine two."

    def test_strips_trailing_whitespace(self):
        text = "Hello   \nWorld   "
        result = clean_email_text(text)
        assert "   " not in result


class TestPrepareEmbeddingText:
    def test_full_fields(self):
        result = prepare_embedding_text("Project Update", "alice@example.com", "The project is on track.")
        assert result.startswith("Subject: Project Update")
        assert "From: alice@example.com" in result
        assert "The project is on track." in result

    def test_empty_body(self):
        result = prepare_embedding_text("Hello", "bob@example.com", "")
        assert "Subject: Hello" in result
        assert "From: bob@example.com" in result
        # No trailing body
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_empty_subject(self):
        result = prepare_embedding_text("", "alice@example.com", "Some content")
        assert "Subject:" not in result
        assert "From: alice@example.com" in result
        assert "Some content" in result

    def test_body_gets_cleaned(self):
        body = "Important info.\n\n-- \nSignature line\nPhone: 123"
        result = prepare_embedding_text("Test", "test@test.com", body)
        assert "Important info." in result
        assert "Signature line" not in result
