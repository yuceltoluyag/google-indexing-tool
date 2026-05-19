import os
import logging


logger = logging.getLogger(__name__)


class PelicanExporter:
    """Exporter to extract published article URLs from a Pelican content folder."""

    def __init__(self, articles_path: str, site_url: str):
        self.articles_path = articles_path
        self.site_url = site_url if site_url.endswith("/") else f"{site_url}/"

    def export_links(self) -> list[str]:
        """Scans the articles path and returns all published article URLs."""
        if not os.path.exists(self.articles_path):
            logger.error(f"Articles path '{self.articles_path}' does not exist.")
            return []

        article_urls = []
        for root, dirs, files in os.walk(self.articles_path):
            for filename in files:
                if filename.endswith(".md") or filename.endswith(".rst"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "Status: published" in content:
                                # Determine language based on folder name 'en' or .en prefix in filename
                                is_english = (
                                    os.path.basename(root) == "en"
                                    or filename.endswith(".en.md")
                                    or filename.endswith(".en.rst")
                                )

                                slug = os.path.splitext(filename)[0]
                                if slug.endswith(".en"):
                                    slug = slug[:-3]

                                if is_english:
                                    article_link = f"{self.site_url}en/{slug}/"
                                else:
                                    article_link = f"{self.site_url}{slug}/"

                                article_urls.append(article_link)
                    except Exception as e:
                        logger.error(f"Error parsing Pelican article {filepath}: {e}")

        logger.info(
            f"Parsed {len(article_urls)} published article URLs from Pelican articles folder."
        )
        return article_urls
