"""
Base scraper class with common functionality for all platform scrapers.
"""
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.config.config import (OUTPUT_DIR, PROXY_API_PARAMS, PROXY_API_URL,
                             REQUEST_DELAY, REQUEST_RETRY, REQUEST_TIMEOUT)


class BaseScraper(ABC):
    """Base scraper class that implements common functionality."""

    def __init__(self, platform_name: str, output_dir: str = "output"):
        """Initialize the scraper.

        Args:
            platform_name (str): Name of the platform being scraped
            output_dir (str): Directory to save results
        """
        self.platform_name = platform_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / f"{platform_name}.json"
        self.session = None
        self.proxy = None
        
        # Configure proxy API
        self.proxy_api_url = "https://api.xiaoxiangdaili.com/ip/get"
        self.proxy_api_params = {
            "appKey": "1208088376956571648",
            "appSecret": "RGxk8zzg",
            "cnt": "",
            "wt": "json",
            "method": "https",
            "city": "",
            "province": ""
        }
        logger.info(f"Initialized {platform_name} scraper")

    async def init_session(self):
        """Initialize aiohttp session with proxy."""
        if self.session is None:
            self.proxy = await self._get_proxy()
            self.session = aiohttp.ClientSession()
            logger.info(f"Initialized session with proxy: {self.proxy}")

    async def close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Closed session")

    async def _get_proxy(self) -> Optional[str]:
        """Get a proxy from the proxy API.

        Returns:
            Optional[str]: Proxy URL if successful, None otherwise
        """
        try:
            response = requests.get(self.proxy_api_url, params=self.proxy_api_params)
            data = response.json()
            logger.debug(f"Proxy API response: {data}")
            
            if data.get("code") == 200 and data.get("data"):
                proxy_info = data["data"][0]
                proxy = f"{proxy_info['ip']}:{proxy_info['port']}"
                proxy_url = f"http://{proxy}"
                logger.info(f"Got new proxy: {proxy_url}")
                return proxy_url
                
            logger.error(f"Failed to get proxy: {data}")
            return None
        except Exception as e:
            logger.error(f"Error getting proxy: {e}")
            return None

    async def _make_request(self, url: str) -> Optional[str]:
        """Make an HTTP request with retry logic.

        Args:
            url (str): URL to request

        Returns:
            Optional[str]: Response text if successful, None otherwise
        """
        for attempt in range(3):  # 3 retries
            try:
                if not self.session:
                    await self.init_session()

                async with self.session.get(
                    url,
                    proxy=self.proxy,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"Request failed with status {response.status}")
            except Exception as e:
                logger.error(f"Request error: {e}")
                await self.close_session()  # Reset session on error
            
            if attempt < 2:  # Don't sleep on last attempt
                wait_time = 2 * (attempt + 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        return None

    def save_results(self, results: List[Dict]):
        """Save scraped results to JSON file.

        Args:
            results (List[Dict]): List of scraped job listings
        """
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(results)} results to {self.output_file}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")

    @abstractmethod
    async def scrape(self, max_pages: int = 5) -> List[Dict]:
        """Scrape job listings from the platform.

        Args:
            max_pages (int, optional): Maximum number of pages to scrape. Defaults to 5.

        Returns:
            List[Dict]: List of scraped job listings
        """
        pass 