#!/usr/bin/env /workspace/tmp_windsurf/venv/bin/python3

import asyncio
import argparse
import sys
import os
from typing import List, Optional
from playwright.async_api import async_playwright
import html5lib
from multiprocessing import Pool
import time
from urllib.parse import urlparse
import logging
import json
from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger
import aiohttp
import aiohttp.client_exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScraper:
    """Web scraper that can handle both static and JavaScript-rendered content."""

    def __init__(self, max_concurrent: int = 3, output_dir: str = "output"):
        """Initialize the scraper.

        Args:
            max_concurrent (int, optional): Maximum number of concurrent requests. Defaults to 3.
            output_dir (str, optional): Directory to save output files. Defaults to "output".
        """
        self.max_concurrent = max_concurrent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        self.browser = None
        self.context = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

    async def __aenter__(self):
        await self.init_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def init_session(self):
        """Initialize sessions for both aiohttp and Playwright."""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.headers['User-Agent']
            )

    async def close(self):
        """Close all sessions."""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None

    async def scrape_with_playwright(self, url: str) -> str:
        """Scrape JavaScript-rendered content using Playwright.

        Args:
            url (str): URL to scrape

        Returns:
            str: HTML content
        """
        if not self.context:
            await self.init_session()
        
        page = await self.context.new_page()
        try:
            # Set longer timeout and wait for network idle
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Wait for potential dynamic content
            await page.wait_for_timeout(5000)  # Wait 5 seconds
            
            # Try to find job listings with JavaScript
            try:
                # Wait for any elements that might indicate job listings
                await page.wait_for_selector('.project-list, .job-list, [class*="project"], [class*="job"]', timeout=10000)
            except:
                logger.debug("No job listing elements found, proceeding with current content")
            
            # Get the final HTML content
            content = await page.content()
            
            # Log page title and URL for debugging
            title = await page.title()
            logger.debug(f"Page title: {title}")
            logger.debug(f"Final URL: {page.url}")
            
            return content
        except Exception as e:
            logger.error(f"Error in Playwright scraping: {str(e)}")
            return None
        finally:
            await page.close()

    async def scrape_page(self, url: str, retry_count: int = 3) -> dict:
        """Scrape a page, using Playwright for sxsapi.com and aiohttp for others.

        Args:
            url (str): URL to scrape
            retry_count (int, optional): Number of retries. Defaults to 3.

        Returns:
            dict: Dictionary containing URL and content
        """
        for attempt in range(retry_count):
            try:
                async with self.semaphore:
                    if 'sxsapi.com' in url:
                        content = await self.scrape_with_playwright(url)
                    else:
                        if not self.session:
                            await self.init_session()
                        
                        async with self.session.get(url, timeout=30) as response:
                            if response.status != 200:
                                logger.error(f"Error fetching {url}: {response.status}")
                                if attempt < retry_count - 1:
                                    await asyncio.sleep(2 * (attempt + 1))
                                    continue
                                return None
                            
                            content = await response.text()
                    
                    logger.debug(f"Received content from {url} (first 1000 chars):\n{content[:1000]}")
                    return {
                        'url': url,
                        'content': content
                    }
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
        return None

    def parse_yuanjisong(self, content: str) -> list:
        """Parse yuanjisong.com job listings.

        Args:
            content (str): HTML content

        Returns:
            list: List of job dictionaries
        """
        soup = BeautifulSoup(content, 'html.parser')
        jobs = []
        
        # Try different selectors for job listings
        job_divs = soup.select('.div_bg_color_fff.div_padding_1.hover1') or \
                  soup.select('.job-item') or \
                  soup.select('.job-listing')
                  
        for div in job_divs:
            try:
                # Try multiple selectors for each field
                title = (
                    div.select_one('.text_type_1.line_clamp_1 b') or
                    div.select_one('.job-title') or
                    div.select_one('h3')
                )
                
                description = (
                    div.select_one('.margin_bottom_10') or
                    div.select_one('.job-description') or
                    div.select_one('.description')
                )
                
                price = (
                    div.select_one('.rixin-text-jobs') or
                    div.select_one('.price') or
                    div.select_one('.job-price')
                )
                
                duration = (
                    div.select_one('.glyphicon-time') or
                    div.select_one('.duration') or
                    div.select_one('.job-duration')
                )
                
                if title:
                    job = {
                        'title': title.text.strip(),
                        'description': description.text.strip() if description else None,
                        'price': price.text.strip() if price else None,
                        'duration': duration.parent.text.strip() if duration else None
                    }
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Error parsing job listing: {str(e)}")
                continue
                
        return jobs

    def clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace and unwanted characters.

        Args:
            text (str): Text to clean

        Returns:
            str: Cleaned text
        """
        if not text:
            return None
            
        # Remove extra whitespace and newlines
        text = ' '.join(text.split())
        
        # Remove unwanted prefixes
        prefixes_to_remove = ['描述：', '项目预算：', '工期：', '￥']
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # Clean up price text
        if '￥' in text or '元' in text:
            # Extract only the price part
            price_parts = []
            for part in text.split():
                if any(c in part for c in ['￥', '元', '千', '万']):
                    price_parts.append(part)
            text = ' '.join(price_parts)
        
        return text.strip() or None

    def parse_sxsapi(self, content: str) -> list:
        """Parse sxsapi.com job listings.

        Args:
            content (str): HTML content

        Returns:
            list: List of job dictionaries
        """
        if not content:
            return []
            
        soup = BeautifulSoup(content, 'html.parser')
        jobs = []
        
        logger.debug("Parsing sxsapi.com content")
        
        # Find all project containers
        project_containers = soup.find_all(class_=lambda x: x and any(word in str(x).lower() for word in ['project', 'job', 'post']))
        
        for container in project_containers:
            try:
                # Look for title in headings or strong tags
                title = None
                title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'strong'])
                if title_elem:
                    title = self.clean_text(title_elem.text)
                
                if not title:
                    continue
                
                # Skip if title looks like noise
                if any(word in title.lower() for word in ['登录', '注册', '首页', '关于', '联系']):
                    continue
                
                # Look for description
                description = None
                desc_elem = container.find(['p', 'div'], class_=lambda x: x and any(word in str(x).lower() for word in ['desc', 'detail', 'content']))
                if desc_elem:
                    description = self.clean_text(desc_elem.text)
                
                # Look for price
                price = None
                price_elem = container.find(string=lambda x: x and any(word in str(x) for word in ['￥', '元', '价格', '预算']))
                if price_elem:
                    price = self.clean_text(price_elem.strip())
                    if price and not any(word in price for word in ['￥', '元', '千', '万']):
                        price = None
                
                # Look for duration
                duration = None
                duration_elem = container.find(string=lambda x: x and any(word in str(x) for word in ['工期', '周期', '天', '月']))
                if duration_elem:
                    duration = self.clean_text(duration_elem.strip())
                    if duration and not any(word in duration for word in ['天', '月', '周']):
                        duration = None
                
                # Only add if we have meaningful data
                if title and (description or price or duration) and len(title) < 100:
                    job = {
                        'title': title,
                        'description': description,
                        'price': price,
                        'duration': duration
                    }
                    
                    # Check if this is a duplicate
                    if not any(j['title'] == job['title'] for j in jobs):
                        jobs.append(job)
                        logger.debug(f"Found job: {job}")
            
            except Exception as e:
                logger.error(f"Error parsing project container: {str(e)}")
                continue
        
        logger.info(f"Found {len(jobs)} jobs on sxsapi.com")
        return jobs

    async def scrape_urls(self, urls: list) -> list:
        """Scrape multiple URLs and parse their content.

        Args:
            urls (list): List of URLs to scrape

        Returns:
            list: List of parsed job listings
        """
        tasks = [self.scrape_page(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results and parse the content
        parsed_results = []
        for result in results:
            if result:
                try:
                    if 'yuanjisong.com' in result['url']:
                        jobs = self.parse_yuanjisong(result['content'])
                        parsed_results.extend(jobs)
                    elif 'sxsapi.com' in result['url']:
                        jobs = self.parse_sxsapi(result['content'])
                        parsed_results.extend(jobs)
                except Exception as e:
                    logger.error(f"Error parsing content from {result['url']}: {str(e)}")
                    continue
                    
        return parsed_results

def parse_html(html_content: Optional[str]) -> str:
    """Parse HTML content and extract text with hyperlinks in markdown format."""
    if not html_content:
        return ""
    
    try:
        document = html5lib.parse(html_content)
        result = []
        seen_texts = set()  # To avoid duplicates
        
        def should_skip_element(elem) -> bool:
            """Check if the element should be skipped."""
            # Skip script and style tags
            if elem.tag in ['{http://www.w3.org/1999/xhtml}script', 
                          '{http://www.w3.org/1999/xhtml}style']:
                return True
            # Skip empty elements or elements with only whitespace
            if not any(text.strip() for text in elem.itertext()):
                return True
            return False
        
        def process_element(elem, depth=0):
            """Process an element and its children recursively."""
            if should_skip_element(elem):
                return
            
            # Handle text content
            if hasattr(elem, 'text') and elem.text:
                text = elem.text.strip()
                if text and text not in seen_texts:
                    # Check if this is an anchor tag
                    if elem.tag == '{http://www.w3.org/1999/xhtml}a':
                        href = None
                        for attr, value in elem.items():
                            if attr.endswith('href'):
                                href = value
                                break
                        if href and not href.startswith(('#', 'javascript:')):
                            # Format as markdown link
                            link_text = f"[{text}]({href})"
                            result.append("  " * depth + link_text)
                            seen_texts.add(text)
                    else:
                        result.append("  " * depth + text)
                        seen_texts.add(text)
            
            # Process children
            for child in elem:
                process_element(child, depth + 1)
            
            # Handle tail text
            if hasattr(elem, 'tail') and elem.tail:
                tail = elem.tail.strip()
                if tail and tail not in seen_texts:
                    result.append("  " * depth + tail)
                    seen_texts.add(tail)
        
        # Start processing from the body tag
        body = document.find('.//{http://www.w3.org/1999/xhtml}body')
        if body is not None:
            process_element(body)
        else:
            # Fallback to processing the entire document
            process_element(document)
        
        # Filter out common unwanted patterns
        filtered_result = []
        for line in result:
            # Skip lines that are likely to be noise
            if any(pattern in line.lower() for pattern in [
                'var ', 
                'function()', 
                '.js',
                '.css',
                'google-analytics',
                'disqus',
                '{',
                '}'
            ]):
                continue
            filtered_result.append(line)
        
        return '\n'.join(filtered_result)
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        return ""

async def process_urls(urls: List[str], max_concurrent: int = 5) -> List[str]:
    """Process multiple URLs concurrently."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            # Create browser contexts
            n_contexts = min(len(urls), max_concurrent)
            contexts = [await browser.new_context() for _ in range(n_contexts)]
            
            # Create tasks for each URL
            tasks = []
            for i, url in enumerate(urls):
                context = contexts[i % len(contexts)]
                task = fetch_page(url, context)
                tasks.append(task)
            
            # Gather results
            html_contents = await asyncio.gather(*tasks)
            
            # Parse HTML contents in parallel
            with Pool() as pool:
                results = pool.map(parse_html, html_contents)
                
            return results
            
        finally:
            # Cleanup
            for context in contexts:
                await context.close()
            await browser.close()

def validate_url(url: str) -> bool:
    """Validate if the given string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

async def main_async(args):
    """Main async function to run the scraper.

    Args:
        args: Command line arguments
    """
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with WebScraper(max_concurrent=args.max_concurrent) as scraper:
        results = await scraper.scrape_urls(args.urls)
        
        # Save results to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Successfully scraped {len(results)} jobs")
        logger.info(f"Results saved to {output_path}")

def main():
    """Run the web scraper from command line."""
    parser = argparse.ArgumentParser(description="Scrape web pages")
    parser.add_argument("urls", nargs="+", help="URLs to scrape")
    parser.add_argument("--max-concurrent", type=int, default=3,
                      help="Maximum number of concurrent requests")
    parser.add_argument("--output", type=str, default="output/results.json",
                      help="Output file path")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Run the scraper
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
    