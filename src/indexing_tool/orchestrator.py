import logging
import time
from datetime import datetime
from typing import Literal

from src.indexing_tool.config import AppConfig
from src.indexing_tool.csv_manager import CSVManager
from src.indexing_tool.pelican_exporter import PelicanExporter
from src.indexing_tool.google_client import (
    GoogleSearchConsoleClient,
    GoogleIndexingApiClient,
)
from src.indexing_tool.bing_client import BingIndexNowClient

logger = logging.getLogger(__name__)


class SmartIndexerOrchestrator:
    """Orchestrates high-level business flows for Pelican site exporting, status checking, and API submissions."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.csv_manager = CSVManager(config.csv_file)

        # Instantiate API clients with Dependency Injection
        self.gsc_client = GoogleSearchConsoleClient(
            service_account_file=config.service_account_file, site_url=config.site_url
        )
        self.google_api_client = GoogleIndexingApiClient(
            service_account_file=config.service_account_file,
            api_url=config.google_api_url,
        )
        self.bing_client = BingIndexNowClient(
            site_url=config.site_url,
            api_key=config.bing_api_key,
            key_location=config.bing_key_location,
        )
        self.pelican_exporter = PelicanExporter(
            articles_path=config.articles_path, site_url=config.site_url
        )

    def export_pelican_links(self) -> None:
        """Finds published Pelican articles and appends new URLs to the CSV tracking database."""
        logger.info("Starting Pelican export process...")
        new_urls = self.pelican_exporter.export_links()
        added_count = self.csv_manager.add_new_links(new_urls)
        if added_count > 0:
            logger.info(
                f"Successfully appended {added_count} new article links to CSV database."
            )
        else:
            logger.info("No new articles to add to CSV database.")

    def run_google_inspect(
        self,
        mode: Literal["single", "newest", "bulk"],
        limit: int = 100,
        specific_url: str = None,
    ) -> None:
        """Queries the Google Search Console API for actual index status and updates CSV."""
        if mode == "single":
            if not specific_url:
                logger.error("No specific URL provided for single inspection.")
                return
            logger.info(f"Inspecting single URL: {specific_url}")
            res = self.gsc_client.inspect_url(specific_url)
            if res["success"]:
                print("-" * 50)
                print(f"Status: [{res['verdict']}]")
                print(f"Details: {res['coverage_state']}")
                print(f"Last Crawl Time: {res['last_crawl']}")
                print(f"Robots.txt Status: {res.get('robots_state', 'UNKNOWN')}")
                print(f"Indexing Allowed: {res.get('indexing_state', 'UNKNOWN')}")
                print(f"Google Canonical: {res.get('google_canonical', 'None')}")
                print("-" * 50)
            else:
                logger.error(f"Failed to inspect URL: {res.get('error')}")
            return

        links = self.csv_manager.load_links()
        if not links:
            logger.info("No URLs found in the tracking CSV.")
            return

        to_inspect = []
        if mode == "newest":
            # Extract the last N links from the list
            to_inspect = [(i, link) for i, link in enumerate(links)][-limit:]
            logger.info(
                f"Checking indexation status for the {len(to_inspect)} newest URLs..."
            )
        elif mode == "bulk":
            # Filter non-PASS URLs, skipping those in active cooldown
            pending_candidates = []
            for i, link in enumerate(links):
                if link.is_google_indexed():
                    continue
                if link.needs_google_cooldown(self.config.cooldown_days):
                    continue
                pending_candidates.append((i, link))

            # Prioritize never-submitted URLs, then oldest submitted ones to avoid starvation loop
            pending_candidates.sort(key=lambda item: item[1].last_successful_submission or "")
            to_inspect = pending_candidates[:limit]
            logger.info(
                f"Checking indexation status for {len(to_inspect)} pending URLs (bulk limit {limit}, cooldown active)..."
            )

        if not to_inspect:
            logger.info("No pending URLs require verification at this time.")
            return

        success_count = 0
        for count, (idx, link) in enumerate(to_inspect):
            logger.info(
                f"[{count + 1}/{len(to_inspect)}] Inspecting status of {link.url}..."
            )
            res = self.gsc_client.inspect_url(link.url)
            if res["success"]:
                link.google_index_status = res["verdict"]
                link.google_index_details = res["coverage_state"]
                link.google_last_crawl = res["last_crawl"]
                success_count += 1
                logger.info(
                    f"  -> Result: [{res['verdict']}] | {res['coverage_state']}"
                )
                self.csv_manager.save_links(links)
            else:
                link.google_index_status = "ERROR"
                link.google_index_details = res.get("error", "API error")
                logger.error(f"  -> Failed: {res.get('error')}")
                self.csv_manager.save_links(links)
                if "403" in str(res.get("error")):
                    logger.critical(
                        "Google API authorization credentials failed. Exiting."
                    )
                    break

            # Short rate limit safety delay
            time.sleep(1)

        logger.info(
            f"Status check workflow complete. Updated {success_count} URL record(s)."
        )

    def run_smart_google_indexing(self, limit: int = 50, dry_run: bool = False) -> None:
        """Inspects status of pending links first, and only submits non-indexed URLs to Google Indexing API."""
        links = self.csv_manager.load_links()
        if not links:
            logger.info("No URLs found in the tracking CSV.")
            return

        to_process = []
        for i, link in enumerate(links):
            if link.is_google_indexed():
                continue
            if link.needs_google_cooldown(self.config.cooldown_days):
                continue
            to_process.append((i, link))

        # Prioritize never-submitted URLs, then oldest submitted ones to avoid starvation loop
        to_process.sort(key=lambda item: item[1].last_successful_submission or "")
        to_process = to_process[:limit]
        if not to_process:
            logger.info(
                "No pending URLs found that require smart inspection or submission (all PASS or under active cooldown)."
            )
            return

        logger.info(
            f"Starting smart indexing workflow for {len(to_process)} URLs (limit: {limit}, cooldown: {self.config.cooldown_days} days)..."
        )
        if dry_run:
            logger.info(
                "[DRY RUN ACTIVE] Simulated run - no actual Google API modifications will be requested."
            )

        processed_count = 0
        submitted_count = 0

        for count, (idx, link) in enumerate(to_process):
            logger.info(
                f"[{count + 1}/{len(to_process)}] Inspecting status of {link.url}..."
            )
            res = self.gsc_client.inspect_url(link.url)
            if res["success"]:
                link.google_index_status = res["verdict"]
                link.google_index_details = res["coverage_state"]
                link.google_last_crawl = res["last_crawl"]

                if link.is_google_indexed():
                    logger.info(
                        f"  -> Already indexed (PASS: {link.google_index_details}). Skipping submission."
                    )
                else:
                    logger.info(
                        f"  -> Not indexed ({link.google_index_status}: {link.google_index_details}). Requesting Indexing API..."
                    )
                    if dry_run:
                        logger.info(
                            f"  [DRY RUN] Would submit URL to Indexing API: {link.url}"
                        )
                        submitted_count += 1
                    else:
                        status_code, resp_text = self.google_api_client.submit_url(
                            link.url
                        )
                        if status_code == 200:
                            logger.info(
                                "  -> Successfully submitted to Google Indexing API. Cooldown initiated."
                            )
                            link.last_successful_submission = datetime.now().isoformat()
                            submitted_count += 1
                        else:
                            logger.error(
                                f"  -> Google Indexing API submission failed ({status_code}): {resp_text}"
                            )
                            if status_code == 429:
                                logger.error(
                                    "  -> Google Indexing API rate limit exceeded. Stopping execution."
                                )
                                self.csv_manager.save_links(links)
                                break

                        # Wait for delay to avoid Google rate limit thresholds
                        time.sleep(self.config.request_delay_seconds)

                processed_count += 1
                self.csv_manager.save_links(links)
            else:
                logger.error(
                    f"  -> GSC Inspection failed for {link.url}: {res.get('error')}"
                )
                if "403" in res.get("error", ""):
                    logger.critical(
                        "GSC API permissions or authorization error. Exiting."
                    )
                    break

            time.sleep(1)

        logger.info(
            f"Smart indexing complete. Processed {processed_count} URLs. Triggered indexing for {submitted_count} URLs."
        )

    def run_bing_submission(self, dry_run: bool = False) -> None:
        """Checks for new URLs without Bing submission timestamps and submits them as a batch to IndexNow API."""
        links = self.csv_manager.load_links()
        if not links:
            logger.info("No URLs found in the tracking CSV.")
            return

        to_submit = []
        indices = []
        for i, link in enumerate(links):
            if not link.bing_last_successful_submission.strip():
                to_submit.append(link.url)
                indices.append(i)

        if not to_submit:
            logger.info("No new URLs to submit to Bing IndexNow.")
            return

        logger.info(f"Found {len(to_submit)} new URLs to submit to Bing IndexNow.")
        if dry_run:
            logger.info(
                f"[DRY RUN ACTIVE] Would submit batch of {len(to_submit)} URLs to Bing IndexNow: {to_submit}"
            )
            return

        status_code, resp_text = self.bing_client.submit_urls(to_submit)
        logger.info(f"Bing IndexNow API submission response status code: {status_code}")

        if status_code in [200, 202]:
            sub_time = datetime.now().isoformat()
            for idx in indices:
                links[idx].bing_last_successful_submission = sub_time
            self.csv_manager.save_links(links)
            logger.info("Updated CSV records with Bing IndexNow submission timestamps.")
        else:
            logger.error(f"Bing IndexNow submission failed with response: {resp_text}")
