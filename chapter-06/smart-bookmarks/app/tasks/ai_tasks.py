import logging
from sqlmodel import Session, select
from app.core.celery_app import celery_app
from app.core.database import engine
from app.models import Bookmark, ProcessingStatus, Tag
from app.services.content_processor import content_processor

logger = logging.getLogger(__name__)


@celery_app.task
def process_bookmark_content(
    bookmark_id: int, user_id: int, request_id: str | None = None
):
    """AI task to process a bookmark's content."""
    # Create a rich log context with all available info
    log_context = {
        "event": "AI_PROCESSING",
        "bookmark_id": bookmark_id,
        "user_id": user_id,
        "request_id": request_id,
    }
    logger.info("Starting AI processing", extra={"extra_info": log_context})
    with Session(engine) as session:
        bookmark = session.get(Bookmark, bookmark_id)
        if not bookmark or not bookmark.ai_enabled:
            logger.warning(f"Skipping AI processing for bookmark_id: {bookmark_id}")
            return

        bookmark.ai_status = ProcessingStatus.PROCESSING
        session.add(bookmark)
        session.commit()

        try:
            clean_html = content_processor.extract_clean_content(bookmark.url)
            title = content_processor.extract_title(clean_html)
            markdown = content_processor.html_to_markdown(clean_html)
            summary = content_processor.generate_summary(markdown)
            tag_names = content_processor.generate_tags(markdown)

            bookmark.title = title
            bookmark.description = summary
            bookmark.tags.clear()
            for name in tag_names:
                tag = session.exec(select(Tag).where(Tag.name == name)).first()
                if not tag:
                    tag = Tag(name=name)
                bookmark.tags.append(tag)

            bookmark.ai_status = ProcessingStatus.COMPLETED
            bookmark.ai_error = None
            # Add structured success log with full context
            log_context["status"] = "SUCCESS"
            log_context["summary_length"] = len(summary)
            log_context["tags_generated"] = tag_names
            logger.info(
                "Successfully processed bookmark", extra={"extra_info": log_context}
            )

        except Exception as e:
            # Fault Tolerance: Handle AI failures gracefully
            bookmark.ai_status = ProcessingStatus.FAILED
            bookmark.ai_error = str(e)[:499]
            bookmark.description = "AI processing failed. Could not generate summary."
            # Add structured failure log with full context
            log_context["status"] = "FAILURE"
            log_context["error"] = str(e)
            logger.error(
                "Failed to process bookmark",
                exc_info=True,
                extra={"extra_info": log_context},
            )

        session.add(bookmark)
        session.commit()
