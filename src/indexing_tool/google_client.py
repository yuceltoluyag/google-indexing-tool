import logging
from typing import Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

logger = logging.getLogger(__name__)


class GoogleSearchConsoleClient:
    """Client for querying the Google Search Console API (URL Inspection)."""

    def __init__(self, service_account_file: str, site_url: str):
        self.service_account_file = service_account_file
        self.site_url = site_url
        self.scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        self._service = None

    def _get_service(self):
        """Lazy-loaded GSC API Service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
            self._service = build(
                "searchconsole", "v1", credentials=credentials, cache_discovery=False
            )
        return self._service

    def inspect_url(self, url: str) -> dict[str, Any]:
        """Inspects a single URL using GSC urlInspection API."""
        try:
            service = self._get_service()
            request_body = {
                "siteUrl": self.site_url,
                "inspectionUrl": url,
                "languageCode": "tr",
            }
            response = (
                service.urlInspection().index().inspect(body=request_body).execute()
            )
            result = response.get("inspectionResult", {})

            index_status = result.get("indexStatusResult", {})
            verdict = index_status.get("verdict", "UNKNOWN")
            coverage_state = index_status.get("coverageState", "No data")
            last_crawl = index_status.get("lastCrawlTime", "Never")
            robots_state = index_status.get("robotsTxtState", "UNKNOWN")
            indexing_state = index_status.get("indexingState", "UNKNOWN")
            google_canonical = index_status.get("googleCanonical", "None")

            return {
                "success": True,
                "verdict": verdict,
                "coverage_state": coverage_state,
                "last_crawl": last_crawl,
                "robots_state": robots_state,
                "indexing_state": indexing_state,
                "google_canonical": google_canonical,
            }
        except HttpError as error:
            error_details = error.reason
            if error.resp.status == 403:
                logger.error(
                    "403 Forbidden: Google Search Console API permission error. "
                    "Check service account configuration and ownership in GSC."
                )
            else:
                logger.error(f"GSC API Error: {error}")
            return {"success": False, "error": error_details}
        except Exception as e:
            logger.error(f"GSC Client Error: {e}")
            return {"success": False, "error": str(e)}


class GoogleIndexingApiClient:
    """Client for calling the Google Indexing API."""

    def __init__(self, service_account_file: str, api_url: str):
        self.service_account_file = service_account_file
        self.api_url = api_url
        self.scopes = ["https://www.googleapis.com/auth/indexing"]
        self._session = None

    def _get_session(self) -> AuthorizedSession:
        """Lazy-loaded authorized session."""
        if self._session is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
            self._session = AuthorizedSession(credentials)
        return self._session

    def submit_url(self, url: str, operation: str = "URL_UPDATED") -> tuple[int, str]:
        """Submits a URL to the Indexing API. Returns (status_code, response_text)."""
        session = self._get_session()
        content = {"url": url, "type": operation}
        try:
            response = session.post(self.api_url, json=content)
            return response.status_code, response.text
        except Exception as e:
            logger.error(f"Google Indexing API Exception for {url}: {e}")
            return 500, str(e)
