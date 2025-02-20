"""
Job scraper implementation using the web_scraper tool.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from loguru import logger

# Fix import path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from tools.web_scraper import WebScraper
from src.config.config import YUANJISONG_URL, SXSAPI_URL


class JobScraper:
    """Job scraper for freelance programming platforms."""

    def __init__(self, output_dir: str = "output"):
        """Initialize the job scraper.

        Args:
            output_dir (str, optional): Directory to save results. Defaults to "output".
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scraper = WebScraper(max_concurrent=3, output_dir=output_dir)

    def _parse_yuanjisong_listing(self, html: str) -> Optional[Dict]:
        """Parse a yuanjisong.com job listing.

        Args:
            html (str): HTML content of the page

        Returns:
            Optional[Dict]: Job details if successful, None otherwise
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract job details (adjust selectors based on actual HTML)
            title = soup.select_one('.job-title')
            description = soup.select_one('.job-description')
            price = soup.select_one('.price')
            deadline = soup.select_one('.deadline')
            post_time = soup.select_one('.post-time')

            return {
                'title': title.text.strip() if title else None,
                'description': description.text.strip() if description else None,
                'price': price.text.strip() if price else None,
                'deadline': deadline.text.strip() if deadline else None,
                'post_time': post_time.text.strip() if post_time else None
            }
        except Exception as e:
            logger.error(f"Error parsing yuanjisong listing: {e}")
            return None

    def _parse_sxsapi_listing(self, html: str) -> Optional[Dict]:
        """Parse a sxsapi.com job listing.

        Args:
            html (str): HTML content of the page

        Returns:
            Optional[Dict]: Job details if successful, None otherwise
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract job details (adjust selectors based on actual HTML)
            title = soup.select_one('.project-title')
            description = soup.select_one('.project-description')
            price = soup.select_one('.project-price')
            deadline = soup.select_one('.project-deadline')
            post_time = soup.select_one('.project-post-time')

            return {
                'title': title.text.strip() if title else None,
                'description': description.text.strip() if description else None,
                'price': price.text.strip() if price else None,
                'deadline': deadline.text.strip() if deadline else None,
                'post_time': post_time.text.strip() if post_time else None
            }
        except Exception as e:
            logger.error(f"Error parsing sxsapi listing: {e}")
            return None

    async def scrape_yuanjisong(self, max_pages: int = 5) -> List[Dict]:
        """Scrape job listings from yuanjisong.com.

        Args:
            max_pages (int, optional): Maximum number of pages to scrape. Defaults to 5.

        Returns:
            List[Dict]: List of job listings
        """
        urls = [YUANJISONG_URL.format(page) for page in range(1, max_pages + 1)]
        results = await self.scraper.scrape_urls(urls, wait_for='.job-list')

        listings = []
        for result in results:
            if result['content']:
                listing = self._parse_yuanjisong_listing(result['content'])
                if listing:
                    listing['url'] = result['url']
                    listings.append(listing)

        # Save results
        output_file = self.output_dir / "yuanjisong.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(listings, f, ensure_ascii=False, indent=2)

        return listings

    async def scrape_sxsapi(self, max_pages: int = 5) -> List[Dict]:
        """Scrape job listings from sxsapi.com.

        Args:
            max_pages (int, optional): Maximum number of pages to scrape. Defaults to 5.

        Returns:
            List[Dict]: List of job listings
        """
        urls = [SXSAPI_URL.format(page) for page in range(1, max_pages + 1)]
        results = await self.scraper.scrape_urls(urls, wait_for='.project-list')

        listings = []
        for result in results:
            if result['content']:
                listing = self._parse_sxsapi_listing(result['content'])
                if listing:
                    listing['url'] = result['url']
                    listings.append(listing)

        # Save results
        output_file = self.output_dir / "sxsapi.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(listings, f, ensure_ascii=False, indent=2)

        return listings

    async def scrape_all(self, max_pages: int = 5) -> Dict[str, List[Dict]]:
        """Scrape job listings from all platforms.

        Args:
            max_pages (int, optional): Maximum number of pages to scrape. Defaults to 5.

        Returns:
            Dict[str, List[Dict]]: Dictionary mapping platform names to their job listings
        """
        tasks = [
            self.scrape_yuanjisong(max_pages),
            self.scrape_sxsapi(max_pages)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            'yuanjisong': results[0] if not isinstance(results[0], Exception) else [],
            'sxsapi': results[1] if not isinstance(results[1], Exception) else []
        } 