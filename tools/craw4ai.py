#!/usr/bin/env python3
"""
Generic web scraping tool using Crawl4AI.
"""
import asyncio
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union
from loguru import logger
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

class WebScraper:
    """Generic web scraper using Crawl4AI."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize the web scraper.
        
        Args:
            output_dir (str): Directory to save results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def scrape_with_schema(self, url: str, schema: Dict, config: Optional[Dict] = None) -> Dict:
        """Scrape content using a CSS selector schema.
        
        Args:
            url (str): URL to scrape
            schema (Dict): CSS selector schema
            config (Optional[Dict]): Additional configuration options
            
        Returns:
            Dict: Scraped content and metadata
        """
        logger.debug(f"Scraping {url} with schema: {json.dumps(schema, indent=2)}")
        
        run_config = CrawlerRunConfig(
            # Core settings
            verbose=True,
            cache_mode=CacheMode.ENABLED,
            
            # Content settings
            word_count_threshold=config.get('word_count_threshold', 10) if config else 10,
            excluded_tags=config.get('excluded_tags', ["nav", "footer"]) if config else ["nav", "footer"],
            exclude_external_links=config.get('exclude_external_links', True) if config else True,
            
            # Page settings
            js_code=config.get('js_code', '') if config else '',
            wait_for=f"css:{schema['baseSelector']}" if 'baseSelector' in schema else None,
            page_timeout=config.get('page_timeout', 30000) if config else 30000,
            
            # Extraction settings
            extraction_strategy=JsonCssExtractionStrategy(schema),
            
            # Anti-bot settings
            simulate_user=config.get('simulate_user', True) if config else True,
            magic=config.get('magic', True) if config else True
        )
        
        logger.debug(f"Using config: {run_config}")
        
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url, config=run_config)
                logger.debug(f"Got result for {url}: success={result.success}")
                
                # Get raw HTML from result
                raw_html = None
                if result.success:
                    try:
                        raw_html = result.html  # Original HTML
                        logger.debug(f"Got HTML from result.html for {url}")
                    except:
                        try:
                            raw_html = result.cleaned_html  # Sanitized HTML
                            logger.debug(f"Got HTML from result.cleaned_html for {url}")
                        except:
                            logger.warning(f"Could not get HTML from result for {url}")
                
                # Get extracted content
                content = None
                if result.success and result.extracted_content:
                    try:
                        # Log raw extracted content
                        logger.debug(f"Raw extracted content from {url}: {result.extracted_content}")
                        
                        # The extracted_content field contains JSON string
                        content = json.loads(result.extracted_content)
                        logger.debug(f"Parsed content from {url}: {json.dumps(content, indent=2)}")
                        
                        # If it's a list with one item, extract that item
                        if isinstance(content, list) and len(content) == 1:
                            content = content[0]
                            logger.debug(f"Extracted single item from list for {url}")
                    except json.JSONDecodeError:
                        # If not JSON, use as is (might be plain text)
                        content = result.extracted_content
                        logger.debug(f"Using raw content for {url} (not JSON)")
                    except Exception as e:
                        logger.error(f"Error parsing extracted content from {url}: {str(e)}")
                else:
                    logger.warning(f"No extracted content for {url}")
                
                response = {
                    'success': result.success,
                    'content': content,
                    'error': result.error_message if not result.success else None,
                    'url': result.url,  # Use final URL in case of redirects
                    'raw_html': raw_html,
                    'status_code': result.status_code,
                    'headers': result.response_headers
                }
                logger.debug(f"Returning response for {url}: {json.dumps(response, indent=2)}")
                return response
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'success': False,
                'content': None,
                'error': str(e),
                'url': url,
                'raw_html': None,
                'status_code': None,
                'headers': None
            }

    async def scrape_batch(self, urls: List[str], schema: Dict, config: Optional[Dict] = None) -> List[Dict]:
        """Scrape multiple URLs using the same schema.
        
        Args:
            urls (List[str]): URLs to scrape
            schema (Dict): CSS selector schema
            config (Optional[Dict]): Additional configuration options
            
        Returns:
            List[Dict]: List of scraped content and metadata
        """
        tasks = [self.scrape_with_schema(url, schema, config) for url in urls]
        return await asyncio.gather(*tasks)

    def save_results(self, results: Union[Dict, List], output_file: str):
        """Save scraped results to a file.
        
        Args:
            results (Union[Dict, List]): Results to save
            output_file (str): Output file path
        """
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved results to {output_path}")

async def main():
    """Run the scraper from command line."""
    parser = argparse.ArgumentParser(description="Generic web scraper using Crawl4AI")
    parser.add_argument("urls", nargs="+", help="URLs to scrape")
    parser.add_argument("--schema", type=str, required=True, help="Path to JSON schema file")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument("--output", type=str, default="results.json", help="Output file name")
    args = parser.parse_args()
    
    # Load schema
    with open(args.schema, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    # Load config if provided
    config = None
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # Run scraper
    scraper = WebScraper()
    results = await scraper.scrape_batch(args.urls, schema, config)
    scraper.save_results(results, args.output)

if __name__ == "__main__":
    asyncio.run(main())