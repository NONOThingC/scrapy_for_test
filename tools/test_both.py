#!/usr/bin/env python3
"""
Test script for running both scrapers.
"""
import os
import sys
import asyncio
from pathlib import Path
from loguru import logger

# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.config import Config
from src.scrapers.yuanjisong_scraper import YuanjisongScraper
from src.scrapers.sxsapi_scraper import SxsapiScraper

# Configure logger to show debug messages
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="DEBUG")

async def main():
    """Run both scrapers and save results."""
    try:
        # Initialize config
        logger.debug("Creating configuration object...")
        config = Config()
        logger.info("Initialized configuration")
        logger.debug(f"Config settings: output_dir={config.output_dir}, proxy_enabled={config.proxy_config.enabled}")
        
        # Create output directory if it doesn't exist
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using output directory: {output_dir}")
        
        # Initialize scrapers
        logger.debug("Initializing scrapers...")
        yuanjisong = YuanjisongScraper(config)
        sxsapi = SxsapiScraper(config)
        logger.info("Initialized scrapers")
        
        # Test yuanjisong.com
        logger.info("Testing yuanjisong.com scraper...")
        try:
            logger.debug("Calling scrape_page(1) on yuanjisong scraper")
            projects = await yuanjisong.scrape_page(1)
            logger.info(f"Found {len(projects)} projects on yuanjisong.com")
            if projects:
                logger.debug(f"First project from yuanjisong: {projects[0]}")
        except Exception as e:
            logger.exception(f"Error testing yuanjisong.com: {str(e)}")
            projects = []
        
        # Test sxsapi.com
        logger.info("Testing sxsapi.com scraper...")
        try:
            logger.debug("Calling scrape_page(1) on sxsapi scraper")
            projects2 = await sxsapi.scrape_page(1)
            logger.info(f"Found {len(projects2)} projects on sxsapi.com")
            if projects2:
                logger.debug(f"First project from sxsapi: {projects2[0]}")
        except Exception as e:
            logger.exception(f"Error testing sxsapi.com: {str(e)}")
            projects2 = []
        
        # Print summary
        logger.info("\nTest Summary:")
        logger.info(f"yuanjisong.com: {len(projects)} projects")
        logger.info(f"sxsapi.com: {len(projects2)} projects")
        
        # Check output files
        for platform in ["yuanjisong", "sxsapi"]:
            output_file = output_dir / f"{platform}.json"
            if output_file.exists():
                size = output_file.stat().st_size
                logger.info(f"Output file {output_file.name}: {size} bytes")
            else:
                logger.warning(f"No output file found for {platform}")
                
    except Exception as e:
        logger.exception(f"Unexpected error in main: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 