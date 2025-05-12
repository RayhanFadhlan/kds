import argparse
import logging
import os
import sys
import time
from datetime import datetime
import json
from typing import List, Dict, Optional

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("batch_scraper.log")
    ]
)

logger = logging.getLogger(__name__)

from src.db import get_db_session
from src.models import Bacteria, ScrapeLog, Base
from src.scrapers.mimedb import MimeDBScraper
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, select, func


class BatchScraper:

    def __init__(
        self,
        batch_size: int = 10,
        delay: float = 2.0,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        max_pages: int = 5,
        progress_file: str = "scraper_progress.json"
    ):
        self.batch_size = batch_size
        self.delay = delay
        self.user_agent = user_agent
        self.max_pages = max_pages if max_pages is not None else 5
        self.progress_file = progress_file
        self.db_session = get_db_session()

        # Create the MimeDB scraper
        self.scraper = MimeDBScraper(
            user_agent=user_agent,
            delay=delay,
            db_session=self.db_session
        )

        # Create scrape log
        self.scrape_log = ScrapeLog(
            start_time=datetime.utcnow(),
            scraping_delay=delay
        )
        self.db_session.add(self.scrape_log)
        self.db_session.commit()

    def get_bacteria_ids(self) -> List[str]:
        return self.scraper.get_bacteria_ids(max_pages=self.max_pages)

    def _load_progress(self) -> Dict:
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading progress file: {e}")

        return {
            "last_processed_idx": -1,
            "successful_ids": [],
            "failed_ids": []
        }

    def _save_progress(self, progress: Dict) -> None:
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f)
        except Exception as e:
            logger.error(f"Error saving progress file: {e}")

    def process_batches(self, max_bacteria: Optional[int] = None) -> None:
        # Get all bacteria IDs
        bacteria_ids = self.get_bacteria_ids()
        logger.info(f"Found {len(bacteria_ids)} bacteria IDs")

        # Apply limit if specified
        if max_bacteria and max_bacteria < len(bacteria_ids):
            bacteria_ids = bacteria_ids[:max_bacteria]
            logger.info(f"Limited to {max_bacteria} bacteria")

        # Load progress
        progress = self._load_progress()
        last_idx = progress["last_processed_idx"]
        successful_ids = set(progress["successful_ids"])
        failed_ids = set(progress["failed_ids"])

        # Calculate total batches
        total_batches = (len(bacteria_ids) + self.batch_size - 1) // self.batch_size

        # Determine starting batch
        start_batch = (last_idx + 1) // self.batch_size

        try:
            # Process each batch
            for batch_idx in range(start_batch, total_batches):
                start_time = time.time()
                batch_start = batch_idx * self.batch_size
                batch_end = min(batch_start + self.batch_size, len(bacteria_ids))
                batch_ids = bacteria_ids[batch_start:batch_end]

                # Skip already processed IDs
                batch_to_process = [bid for bid in batch_ids if bid not in successful_ids and bid not in failed_ids]

                logger.info(f"Processing batch {batch_idx+1}/{total_batches} with {len(batch_to_process)} bacteria to process")

                # Skip if batch is empty
                if not batch_to_process:
                    logger.info(f"Batch {batch_idx+1} already fully processed, skipping")
                    continue

                # Process batch
                batch_data = []
                local_successful = []
                local_failed = []

                for bacteria_id in batch_to_process:
                    try:
                        bacteria_data = self.scraper.scrape_bacteria(bacteria_id)
                        if bacteria_data:
                            batch_data.append(bacteria_data)
                            local_successful.append(bacteria_id)
                        else:
                            local_failed.append(bacteria_id)
                    except Exception as e:
                        logger.error(f"Error scraping bacteria {bacteria_id}: {e}")
                        local_failed.append(bacteria_id)

                # Save batch to database
                if batch_data:
                    try:
                        self._save_batch_to_db(batch_data)
                        # Update successful IDs
                        successful_ids.update(local_successful)
                        logger.info(f"Successfully saved {len(local_successful)} bacteria to database")
                    except Exception as e:
                        logger.error(f"Error saving batch to database: {e}")
                        # Mark all as failed
                        failed_ids.update(local_successful)

                # Update failed IDs
                failed_ids.update(local_failed)

                # Update progress
                progress = {
                    "last_processed_idx": batch_end - 1,
                    "successful_ids": list(successful_ids),
                    "failed_ids": list(failed_ids)
                }
                self._save_progress(progress)

                # Calculate batch timing
                batch_time = time.time() - start_time
                logger.info(f"Batch {batch_idx+1} completed in {batch_time:.2f} seconds")

                # Update scrape log
                self.scrape_log.successful_scrapes = len(successful_ids)
                self.scrape_log.failed_scrapes = len(failed_ids)
                self.db_session.commit()

            # Update final scrape log
            self.scrape_log.end_time = datetime.utcnow()
            self.scrape_log.total_urls = len(bacteria_ids)
            self.scrape_log.successful_scrapes = len(successful_ids)
            self.scrape_log.failed_scrapes = len(failed_ids)
            self.db_session.commit()

            logger.info(f"Scraping completed: {len(successful_ids)} successful, {len(failed_ids)} failed")

        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
            self.scrape_log.end_time = datetime.utcnow()
            self.scrape_log.error_message = "Interrupted by user"
            self.db_session.commit()
        except Exception as e:
            logger.exception(f"Scraping failed: {e}")
            self.scrape_log.end_time = datetime.utcnow()
            self.scrape_log.error_message = str(e)
            self.db_session.commit()
        finally:
            # Save final progress
            final_progress = {
                "last_processed_idx": max(last_idx, progress.get("last_processed_idx", -1)),
                "successful_ids": list(successful_ids),
                "failed_ids": list(failed_ids)
            }
            self._save_progress(final_progress)

    def _save_batch_to_db(self, batch_data: List[Dict]) -> None:
        try:
            # Begin transaction
            self.db_session.begin()

            for data in batch_data:
                # Check for existing record
                existing = self.db_session.query(Bacteria).filter(
                    Bacteria.bacteria_id == data["bacteria_id"]
                ).first()

                if existing:
                    # Update existing record
                    for key, value in data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # Create new record
                    bacteria = Bacteria(**data)
                    self.db_session.add(bacteria)

            # Commit transaction
            self.db_session.commit()

        except Exception as e:
            # Rollback on error
            self.db_session.rollback()
            logger.exception(f"Error saving batch to database: {e}")
            raise

    def get_stats(self) -> Dict:
        stats = {}

        try:
            # Total count
            stats["total"] = self.db_session.query(func.count(Bacteria.id)).scalar() or 0

            # Pathogen counts
            stats["pathogenic"] = self.db_session.query(func.count(Bacteria.id)).filter(
                Bacteria.is_pathogen == True
            ).scalar() or 0

            stats["non_pathogenic"] = self.db_session.query(func.count(Bacteria.id)).filter(
                Bacteria.is_pathogen == False
            ).scalar() or 0

            # Gram stain counts
            stats["gram_positive"] = self.db_session.query(func.count(Bacteria.id)).filter(
                Bacteria.gram_stain == "Positive"
            ).scalar() or 0

            stats["gram_negative"] = self.db_session.query(func.count(Bacteria.id)).filter(
                Bacteria.gram_stain == "Negative"
            ).scalar() or 0

        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return stats

    def close(self) -> None:
        self.db_session.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Batch scraper for bacteria data")

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of items to process in each batch (default: 10)"
    )

    parser.add_argument(
        "--max-bacteria",
        type=int,
        default=None,
        help="Maximum number of bacteria to process (default: all)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,  # Default to 5 pages
        help="Maximum number of pages to scrape (default: 5)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)"
    )

    parser.add_argument(
        "--progress-file",
        type=str,
        default="scraper_progress.json",
        help="File to store progress for resuming (default: scraper_progress.json)"
    )

    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Reset progress and start from beginning"
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show database statistics, don't scrape"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Reset progress if requested
    if args.reset_progress and os.path.exists(args.progress_file):
        os.remove(args.progress_file)
        logger.info(f"Reset progress file: {args.progress_file}")

    # Create batch scraper
    batch_scraper = BatchScraper(
        batch_size=args.batch_size,
        delay=args.delay,
        max_pages=args.max_pages,
        progress_file=args.progress_file
    )

    try:
        if args.stats_only:
            # Show stats only
            stats = batch_scraper.get_stats()
            logger.info("Database statistics:")
            logger.info(f"- Total bacteria: {stats['total']}")
            if stats['total'] > 0:
                logger.info(f"- Pathogenic: {stats['pathogenic']} ({stats['pathogenic']/stats['total']*100:.1f}%)")
                logger.info(f"- Non-pathogenic: {stats['non_pathogenic']} ({stats['non_pathogenic']/stats['total']*100:.1f}%)")
                logger.info(f"- Gram positive: {stats['gram_positive']} ({stats['gram_positive']/stats['total']*100:.1f}%)")
                logger.info(f"- Gram negative: {stats['gram_negative']} ({stats['gram_negative']/stats['total']*100:.1f}%)")
            else:
                logger.info("- No bacteria in database")
        else:
            # Process batches
            batch_scraper.process_batches(max_bacteria=args.max_bacteria)
    finally:
        batch_scraper.close()


if __name__ == "__main__":
    main()
