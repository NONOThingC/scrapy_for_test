"""
Main script to run the job listing scrapers.
"""
import asyncio
import json
from pathlib import Path
import sys

from loguru import logger

from src.scrapers.yuanjisong_scraper import YuanjisongScraper
from src.scrapers.sxsapi_scraper import SxsapiScraper


def setup_logging():
    """Set up logging configuration."""
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    logger.remove()  # Remove default handler
    
    # Add handlers for both file and console output
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO"
    )
    logger.add(
        log_path / "scraper.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG"
    )


async def main():
    """Run the job listing scrapers."""
    setup_logging()
    logger.info("Starting job listing scrapers")

    try:
        # Create scrapers
        scrapers = [
            YuanjisongScraper(),
            SxsapiScraper()
        ]
        
        # Run scrapers concurrently
        tasks = [scraper.scrape(max_pages=1) for scraper in scrapers]  # Start with 1 page for testing
        results = await asyncio.gather(*tasks)
        
        # Combine results
        combined_results = {}
        for scraper, jobs in zip(scrapers, results):
            combined_results[scraper.platform_name] = jobs
            logger.info(f"Successfully scraped {len(jobs)} listings from {scraper.platform_name}")
        
        # Save combined results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / "all_jobs.json", 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, ensure_ascii=False, indent=2)
        logger.info("Saved combined results")

    except Exception as e:
        logger.error(f"Error running scrapers: {e}")
        sys.exit(1)

    logger.info("Finished scraping job listings")


if __name__ == "__main__":
    asyncio.run(main()) 