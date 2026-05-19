import configparser
from pydantic import BaseModel
from typing import Any


class AppConfig(BaseModel):
    """Pydantic model validating configuration options loaded from config.ini."""

    articles_path: str
    site_url: str
    csv_file: str
    service_account_file: str
    log_file: str
    google_api_url: str
    request_delay_seconds: int
    cooldown_days: int
    bing_api_key: str
    bing_key_location: str

    @classmethod
    def load_from_file(cls, filepath: str = "config.ini") -> "AppConfig":
        """Reads config.ini, flattens variables, and loads them into AppConfig."""
        config = configparser.ConfigParser()
        config.read(filepath)

        flat_data: dict[str, Any] = {}
        # Load from all sections
        for section in config.sections():
            for key, val in config.items(section):
                flat_data[key.lower()] = val
        # Load default fallback items
        for key, val in config.items("DEFAULT"):
            flat_data[key.lower()] = val

        return cls(
            articles_path=flat_data.get("articles_path", "content/articles"),
            site_url=flat_data.get("site_url", ""),
            csv_file=flat_data.get("csv_file", "article_links.csv"),
            service_account_file=flat_data.get("service_account_file", ""),
            log_file=flat_data.get("log_file", "indexing.log"),
            google_api_url=flat_data.get(
                "url", "https://indexing.googleapis.com/v3/urlNotifications:publish"
            ),
            request_delay_seconds=int(flat_data.get("request_delay_seconds", 10)),
            cooldown_days=int(flat_data.get("cooldown_days", 3)),
            bing_api_key=flat_data.get("api_key", ""),
            bing_key_location=flat_data.get("key_location", ""),
        )
