from unittest.mock import MagicMock
from sqlmodel import Session
from app.models import Bookmark, ProcessingStatus, User
from app.tasks.ai_tasks import process_bookmark_content


def test_process_bookmark_content(session: Session, test_user: User, monkeypatch):
    """Test the AI processing task by mocking the AI service."""
    # Arrange: Create a pending bookmark
    bookmark = Bookmark(
        url="https://example.com",
        title="Test",
        user_id=test_user.id,
        ai_enabled=True,
        ai_status=ProcessingStatus.PENDING,
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)

    # Mock the content_processor to avoid real network calls
    mock_processor = MagicMock()
    mock_processor.extract_clean_content.return_value = "Clean HTML Content"
    # Add a mock for the extract_title method
    mock_processor.extract_title.return_value = "Mocked Title"
    mock_processor.html_to_markdown.return_value = "Clean markdown"
    mock_processor.generate_summary.return_value = "Mocked AI summary."
    mock_processor.generate_tags.return_value = ["mocked", "ai", "tag"]
    monkeypatch.setattr("app.tasks.ai_tasks.content_processor", mock_processor)

    # Monkeypatch the engine for the test database
    test_engine = session.get_bind()
    monkeypatch.setattr("app.tasks.ai_tasks.engine", test_engine)

    # Act: Run the task function directly
    process_bookmark_content(bookmark_id=bookmark.id, user_id=test_user.id)

    # Assert: Check the bookmark was updated with mocked data
    session.refresh(bookmark)
    assert bookmark.ai_status == ProcessingStatus.COMPLETED
    assert bookmark.title == "Mocked Title"  # Assert the new title
    assert bookmark.description == "Mocked AI summary."
    assert "mocked" in [tag.name for tag in bookmark.tags]
