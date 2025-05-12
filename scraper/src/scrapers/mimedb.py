import logging
import re
import time
import sys
import os
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class MimeDBScraper:

    BASE_URL = "https://mimedb.org"
    MICROBES_URL = f"{BASE_URL}/microbes"

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        delay: float = 2.0,
        db_session: Optional[Session] = None
    ):
        self.user_agent = user_agent
        self.delay = delay
        self.db_session = db_session
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

    def get_page(self, url: str, retries: int = 3) -> Optional[str]:

        for attempt in range(retries):
            try:
                time.sleep(self.delay)

                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=120
                )

                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"Got status code {response.status_code} on attempt {attempt+1}")
                    time.sleep(self.delay)
            except Exception as e:
                logger.exception(f"Error fetching {url} on attempt {attempt+1}: {e}")
                time.sleep(self.delay)

        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None

    def get_bacteria_ids(self, max_pages: int = 5) -> List[str]:
        bacteria_ids = []

        max_pages = 5 if max_pages is None else max_pages

        logger.info(f"Scraping up to {max_pages} pages")

        for page in range(1, max_pages + 1):
            page_url = f"{self.MICROBES_URL}?page={page}"
            logger.info(f"Fetching bacteria list page {page}/{max_pages}")

            html_content = self.get_page(page_url)
            if not html_content:
                logger.error(f"Failed to get page {page}, skipping")
                continue

            soup = BeautifulSoup(html_content, "html.parser")

            for link in soup.select("td.microbe-link a.btn-card"):
                bacteria_id = link.get("href").split("/")[-1]
                if bacteria_id and bacteria_id.startswith("MMDBm"):
                    bacteria_ids.append(bacteria_id)

            logger.info(f"Found {len(bacteria_ids)} bacteria IDs so far")

        return bacteria_ids

    def parse_bacteria_page(self, html_content: str) -> Dict:
        soup = BeautifulSoup(html_content, "html.parser")

        data = {}

        title_elem = soup.select_one(".page-header h1")
        if title_elem:
            full_title = title_elem.text.strip()
            match = re.match(r"(.*?) \((MMDBm\d+)\)", full_title)
            if match:
                data["name"] = match.group(1)
                data["bacteria_id"] = match.group(2)
            else:
                data["name"] = full_title

        taxinfo_section = soup.find("tbody", {"id": "taxinfo"})
        if taxinfo_section:
            taxonomy_mapping = {
                "Superkingdom": "superkingdom",
                "Kingdom": "kingdom",
                "Phylum": "phylum",
                "Class": "class_name",
                "Order": "order",
                "Family": "family",
                "Genus": "genus",
                "Species": "species",
                "Strain": "strain"
            }

            for row in taxinfo_section.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) == 2:
                    header = cells[0].text.strip()
                    value = cells[1].text.strip()

                    if header in taxonomy_mapping:
                        data[taxonomy_mapping[header]] = value

        properties_section = soup.find("tbody", {"id": "microbe-properties"})
        if properties_section:
            properties_mapping = {
                "Gram staining properties": "gram_stain",
                "Shape": "shape",
                "Mobility": "mobility",
                "Flagellar presence": "flagellar_presence",
                "Number of membranes": "number_of_membranes",
                "Oxygen preference": "oxygen_preference",
                "Optimal temperature": "optimal_temperature",
                "Temperature range": "temperature_range",
                "Habitat": "habitat",
                "Biotic relationship": "biotic_relationship",
                "Cell arrangement": "cell_arrangement",
                "Sporulation": "sporulation",
                "Metabolism": "metabolism",
                "Energy source": "energy_source"
            }

            for row in properties_section.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) == 2:
                    header = cells[0].text.strip()
                    value_cell = cells[1]

                    not_available = value_cell.find("span", class_="wishart-not-available")
                    if not_available:
                        value = None
                    else:
                        value = value_cell.text.strip()

                    if header in properties_mapping:
                        field_name = properties_mapping[header]

                        if field_name in ["mobility", "flagellar_presence", "sporulation"]:
                            if value:
                                value = value.lower() == "yes" or value.lower() == "true"

                        if field_name == "optimal_temperature" and value and value != "Not Available":
                            try:
                                match = re.search(r'(\d+(\.\d+)?)', value)
                                if match:
                                    value = float(match.group(1))
                            except ValueError:
                                value = None

                        data[field_name] = value

        pathogenicity_section = soup.find("td", class_="microbe-disease")
        if pathogenicity_section:
            pathogenicity_text = pathogenicity_section.text.strip().lower()
            data["is_pathogen"] = "pathogenic" in pathogenicity_text

        return data

    def scrape_bacteria(self, bacteria_id: str) -> Optional[Dict]:
        detail_url = f"{self.BASE_URL}/microbes/{bacteria_id}"
        logger.info(f"Scraping bacterium: {bacteria_id}")

        html_content = self.get_page(detail_url)
        if not html_content:
            logger.error(f"Failed to get page for {bacteria_id}")
            return None

        bacteria_data = self.parse_bacteria_page(html_content)
        logger.info(f"Successfully scraped data for {bacteria_id}: {bacteria_data.get('name')}")

        return bacteria_data

    def save_bacteria(self, bacteria_data: Dict, duplicate_action: str = "update") -> bool:
        if not self.db_session:
            logger.error("No database session available")
            return False

        try:
            from src.models import Bacteria

            existing = self.db_session.query(Bacteria).filter(
                Bacteria.bacteria_id == bacteria_data["bacteria_id"]
            ).first()

            if existing:
                logger.info(f"Bacteria {bacteria_data['bacteria_id']} already exists in database")

                if duplicate_action == "skip":
                    logger.info(f"Skipping existing bacteria {bacteria_data['bacteria_id']} (skip action selected)")
                    return True

                elif duplicate_action == "update":
                    logger.info(f"Updating existing bacteria {bacteria_data['bacteria_id']} (update action selected)")
                    for key, value in bacteria_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)

                    self.db_session.commit()
                    logger.info(f"Successfully updated bacteria {bacteria_data['bacteria_id']}")
                    return True

                elif duplicate_action == "force":
                    logger.info(f"Removing existing bacteria {bacteria_data['bacteria_id']} for re-insertion (force action selected)")
                    self.db_session.delete(existing)
                    self.db_session.commit()

                else:
                    logger.warning(f"Unknown duplicate action '{duplicate_action}', defaulting to update")
                    for key, value in bacteria_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)

                    self.db_session.commit()
                    return True

            bacteria = Bacteria(**bacteria_data)
            self.db_session.add(bacteria)
            self.db_session.commit()

            logger.info(f"Saved bacteria {bacteria_data['bacteria_id']} to database")
            return True

        except Exception as e:
            logger.exception(f"Error saving bacteria {bacteria_data.get('bacteria_id')}: {e}")
            self.db_session.rollback()
            return False
