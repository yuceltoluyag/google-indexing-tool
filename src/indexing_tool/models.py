from datetime import datetime
from pydantic import BaseModel


class ArticleLink(BaseModel):
    """Pydantic model representing a single article row in the tracking CSV."""

    url: str
    last_successful_submission: str = ""
    bing_last_successful_submission: str = ""
    google_index_status: str = ""
    google_index_details: str = ""
    google_last_crawl: str = ""

    def is_google_indexed(self) -> bool:
        """Returns True if the URL is successfully indexed by Google."""
        return self.google_index_status == "PASS"

    def needs_google_cooldown(self, cooldown_days: int) -> bool:
        """Returns True if the URL was recently submitted and is still under cooldown."""
        if not self.last_successful_submission:
            return False
        try:
            sub_date = datetime.fromisoformat(self.last_successful_submission)
            delta = datetime.now() - sub_date
            return delta.days < cooldown_days
        except Exception:
            return False
