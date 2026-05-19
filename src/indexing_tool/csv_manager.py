import csv
import os
from src.indexing_tool.models import ArticleLink


class CSVManager:
    """Manages reading and writing ArticleLink models to the tracking CSV file."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.headers = [
            "url",
            "last_successful_submission",
            "bing_last_successful_submission",
            "google_index_status",
            "google_index_details",
            "google_last_crawl",
        ]

    def load_links(self) -> list[ArticleLink]:
        """Loads all article links from the CSV, parsing them into ArticleLink models."""
        if not os.path.exists(self.filepath):
            return []

        links = []
        with open(self.filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []

            for row in reader:
                link = ArticleLink(
                    url=row.get("url", "").strip(),
                    last_successful_submission=row.get(
                        "last_successful_submission", ""
                    ).strip(),
                    bing_last_successful_submission=row.get(
                        "bing_last_successful_submission", ""
                    ).strip(),
                    google_index_status=row.get("google_index_status", "").strip(),
                    google_index_details=row.get("google_index_details", "").strip(),
                    google_last_crawl=row.get("google_last_crawl", "").strip(),
                )
                if link.url:
                    links.append(link)
        return links

    def save_links(self, links: list[ArticleLink]) -> None:
        """Saves the list of ArticleLink models back to the CSV file."""
        with open(self.filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()
            for link in links:
                # Pydantic v2 dump
                writer.writerow(link.model_dump())

    def add_new_links(self, new_urls: list[str]) -> int:
        """Appends new URLs to the CSV if they do not already exist. Returns count of added URLs."""
        existing_links = self.load_links()
        existing_urls = {link.url.strip() for link in existing_links}

        added_count = 0
        updated_links = list(existing_links)
        for url in new_urls:
            url_clean = url.strip()
            if url_clean and url_clean not in existing_urls:
                updated_links.append(ArticleLink(url=url_clean))
                added_count += 1

        if added_count > 0:
            self.save_links(updated_links)

        return added_count
