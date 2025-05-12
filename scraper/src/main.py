import argparse
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log")
    ]
)

logger = logging.getLogger(__name__)

from src.db import get_db_session
from src.models import ScrapeLog, Base
from src.scrapers.mimedb import MimeDBScraper
from src.init_db import init_db

def parse_args():
    parser = argparse.ArgumentParser(description="Bacteria data scraper for MiMeDB")

    parser.add_argument(
        "--max-bacteria",
        type=int,
        default=None,
        help="Maximum number of bacteria to scrape (default: all)"
    )

    parser.add_argument(
        "--scraping-delay",
        type=float,
        default=float(os.getenv("SCRAPING_DELAY", "2.0")),
        help="Delay in seconds between requests (default: 2.0)"
    )

    parser.add_argument(
        "--user-agent",
        type=str,
        default=os.getenv("SCRAPER_USER_AGENT",
                         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
        help="User agent string to use (default: from environment)"
    )

    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the database before scraping"
    )

    parser.add_argument(
        "--duplicate-action",
        type=str,
        choices=["update", "skip", "force"],
        default="update",
        help="How to handle duplicate bacteria records: update existing, skip, or force override (default: update)"
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        default=True,
        help="Continue processing if an error occurs (default: True)"
    )

    return parser.parse_args()

def main():
    args = parse_args()

    logger.info("Starting bacteria scraper")
    logger.info(f"Configuration: max_bacteria={args.max_bacteria}, duplicate_action={args.duplicate_action}")

    if args.init_db:
        logger.info("Initializing database")
        init_success = init_db()
        if not init_success:
            logger.error("Database initialization failed, exiting.")
            return

    db_session = get_db_session()

    try:
        scrape_log = ScrapeLog(
            start_time=datetime.utcnow(),
            scraping_delay=args.scraping_delay
        )

        try:
            db_session.add(scrape_log)
            db_session.commit()
            logger.info("Created scrape log entry")
        except Exception as e:
            logger.error(f"Error creating scrape log: {e}")
            logger.warning("Tables may not exist. Initializing database...")
            db_session.rollback()

            init_success = init_db()
            if not init_success:
                logger.error("Database initialization failed, exiting.")
                return

            scrape_log = ScrapeLog(
                start_time=datetime.utcnow(),
                scraping_delay=args.scraping_delay
            )
            db_session.add(scrape_log)
            db_session.commit()

        scraper = MimeDBScraper(
            user_agent=args.user_agent,
            delay=args.scraping_delay,
            db_session=db_session
        )

        start_time = time.time()
        scraped_ids = scraper.scrape_and_save(
            max_bacteria=args.max_bacteria,
            duplicate_action=args.duplicate_action,
            continue_on_error=args.continue_on_error
        )
        end_time = time.time()

        scrape_log.end_time = datetime.utcnow()
        scrape_log.total_urls = len(scraped_ids) if scraped_ids else 0
        scrape_log.successful_scrapes = len(scraped_ids) if scraped_ids else 0
        scrape_log.failed_scrapes = 0
        db_session.commit()

        logger.info(f"Scraping completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Successfully scraped {len(scraped_ids)} bacteria")

    except Exception as e:
        logger.exception(f"Scraping failed: {e}")

        if 'scrape_log' in locals() and scrape_log:
            scrape_log.end_time = datetime.utcnow()
            scrape_log.error_message = str(e)
            db_session.commit()

    finally:
        db_session.close()

if __name__ == "__main__":
    main()
