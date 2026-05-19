from typing import Protocol, Any


class StatusChecker(Protocol):
    """Protocol for checking actual URL indexation status in search engines."""

    def inspect_url(self, url: str) -> dict[str, Any]:
        """Inspects the given URL and returns inspection details.

        Returned dict contains keys:
        - success: bool
        - verdict: str (e.g. 'PASS', 'NEUTRAL', 'FAIL')
        - coverage_state: str
        - last_crawl: str
        - error: str (optional)
        """
        ...


class IndexingClient(Protocol):
    """Protocol for sending indexing submissions to search engine APIs."""

    def submit_urls(self, urls: list[str]) -> tuple[int, str]:
        """Submits list of URLs for indexing.

        Returns:
            tuple[int, str]: (status_code, response_text)
        """
        ...
