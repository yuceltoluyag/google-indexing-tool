import requests
import logging

logger = logging.getLogger(__name__)


class BingIndexNowClient:
    """Client for submitting batch URL indexing requests to the Bing IndexNow API."""

    def __init__(self, site_url: str, api_key: str, key_location: str):
        self.site_url = site_url
        self.api_key = api_key
        self.key_location = key_location
        self.api_url = "https://api.indexnow.org/IndexNow"

    def submit_urls(self, urls: list[str]) -> tuple[int, str]:
        """Submits a bulk list of URLs to Bing IndexNow."""
        if not urls:
            return 200, "No URLs to submit."

        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "host": self.site_url,
            "key": self.api_key,
            "keyLocation": self.key_location,
            "urlList": urls,
        }

        try:
            logger.info(f"Submitting {len(urls)} URLs to Bing IndexNow...")
            response = requests.post(
                self.api_url, headers=headers, json=data, timeout=15
            )
            return response.status_code, response.text
        except Exception as e:
            logger.error(f"Bing IndexNow API submission failed: {e}")
            return 500, str(e)
