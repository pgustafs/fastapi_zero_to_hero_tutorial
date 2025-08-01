import logging
import re
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from docling.datamodel.document import InputDocument, InputFormat
from docling.backend.html_backend import HTMLDocumentBackend
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class ContentProcessor:
    """A service to extract, clean, and analyze web content using AI."""

    def __init__(self):
        self.ai_client = OpenAI(
            api_key=settings.AI_API_KEY, base_url=settings.AI_API_BASE_URL
        )

    def extract_clean_content(self, url: str) -> BeautifulSoup:
        """Extracts clean HTML content from a URL."""
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            boilerplate_re = re.compile(
                r".*(footer|header|navigation|nav|sidebar|menu).*", re.I
            )
            static_tags = ["script", "style", "noscript", "iframe", "aside"]

            tags_to_remove = soup.find_all(name=boilerplate_re) + soup.find_all(
                static_tags
            )
            for tag in tags_to_remove:
                tag.decompose()

            # return soup.encode('utf-8')
            return soup
        except requests.RequestException as e:
            raise Exception(f"Error fetching {url}: {e}") from e

    @staticmethod
    def extract_title(soup: BeautifulSoup) -> str:
        """Extract the page title from <title> or <h1>. Return fallback if none found."""
        try:
            # Try <title> tag
            if soup.title and soup.title.string:
                return soup.title.string.strip()

            # Try first <h1> tag
            h1 = soup.find("h1")
            if h1 and h1.text:
                return h1.text.strip()

        except Exception:
            # Optional: log or print the error if needed
            pass

        # Fallback title
        return "title not found"

    def html_to_markdown(self, clean_html: bytes) -> str:
        """Converts clean HTML bytes to markdown."""
        try:
            clean_html_utf8 = clean_html.encode("utf-8")
            html_stream = BytesIO(clean_html_utf8)

            in_doc = InputDocument(
                path_or_stream=BytesIO(clean_html_utf8),
                format=InputFormat.HTML,
                backend=HTMLDocumentBackend,
                filename="content.html",
            )
            backend = HTMLDocumentBackend(in_doc=in_doc, path_or_stream=html_stream)
            doc = backend.convert()
            markdown = doc.export_to_markdown()
            return re.sub(r"\n{3,}", "\n\n", markdown).strip()
        except Exception as e:
            raise Exception(f"Error converting HTML to markdown: {e}") from e

    def _call_ai_model(self, system_prompt: str, user_content: str) -> str:
        """Helper function to make calls to an OpenAI-compatible API."""
        try:
            response = self.ai_client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=4096,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling AI model: {e}")
            raise Exception(f"AI API call failed: {e}") from e

    def generate_summary(self, markdown_content: str) -> str:
        """Generates a summary from markdown content."""
        # SYSTEM_PROMPT = """
        # You are an intelligent web content analyst for a bookmarking service. Create a concise summary (under 80 words) that captures the essence of the content. Focus on the main topic, key points, and purpose. Do not use introductory phrases like 'This article...'.
        # """
        SYSTEM_PROMPT = """
        You are an intelligent web content analyst for a sophisticated bookmarking service. Your primary function is to create a dense 'highlight' summary from the text of a webpage. This highlight serves as a quick, informative preview for the user's saved bookmarks.

        When creating the highlight, focus on extracting:
        1.  **The core subject and main topic.**
        2.  **Key entities mentioned (e.g., people, companies, products, technologies).**
        3.  **The main takeaway, conclusion, or purpose of the content (e.g., is it a news report, a how-to guide, an opinion piece, a product review?).**

        The final output must be a single, well-written paragraph. It must be extremely concise to fit within a 512-token limit for a downstream embedding model. For this reason, keep the summary under 400 words. Do not use introductory phrases like 'This article is about...' or 'The content discusses...'. Jump directly into the highlight.
        """
        user_content = (
            "Please generate a highlight summary for the following content:\n\n"
            + markdown_content[:10000]
        )
        return self._call_ai_model(SYSTEM_PROMPT, user_content)

    def generate_tags(self, markdown_content: str) -> list[str]:
        """Generates a list of tags from markdown content."""
        SYSTEM_PROMPT = """
        You are an expert content categorization engine for a bookmarking application. Your sole purpose is to analyze the provided text and generate exactly 5 relevant tags to help users organize and find their bookmarks.

        Instructions:
        1.  **Analyze the content** to identify the primary subjects, technologies, themes, and key entities.
        2.  **Generate exactly 6 tags.** No more, no less.
        3.  **Tags must be concise**, ideally 1-3 words.
        4.  **Format all tags in lowercase** and replace spaces with a hyphen (kebab-case).
        5.  **Provide the output as a single line of comma-separated values.** Do not add a numbered list, bullet points, or any introductory text like "Here are the tags:".

        Example output:
        web-development,react-js,front-end,state-management,tutorial,python
        """
        user_content = (
            "Generate 6 tags for the following content:\n\n" + markdown_content[:10000]
        )

        tags_str = self._call_ai_model(SYSTEM_PROMPT, user_content)
        # Clean up the AI's output
        return [tag.strip() for tag in tags_str.split(",") if tag.strip()]


# Create a single, reusable instance for the application
content_processor = ContentProcessor()
