"""
Test script to verify yuanjisong.com scraper functionality.
"""
import asyncio
import json
from pathlib import Path
from loguru import logger

from src.scrapers.yuanjisong_scraper import YuanjisongScraper
from src.config.config import Config

async def test_yuanjisong():
    """Test the yuanjisong.com scraper."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize config
    config = Config()
    config.output_dir = str(output_dir)
    
    # Initialize scraper
    scraper = YuanjisongScraper(config=config)
    
    try:
        # Test list page scraping
        logger.info("Testing list page scraping...")
        projects = await scraper.scrape_list_page(1)
        
        if projects:
            logger.info(f"\nFound {len(projects)} projects on first page:")
            for project in projects[:3]:  # Show first 3 projects
                logger.info(f"\nProject: {project['title']}")
                logger.info(f"URL: {project['url']}")
                logger.info(f"Price: {project['price']}")
                logger.info(f"Duration: {project['duration']}")
                
            # Save list page results
            with open(output_dir / "yuanjisong_list.json", "w", encoding="utf-8") as f:
                json.dump(projects, f, ensure_ascii=False, indent=2)
            logger.info("\nSaved list page results to yuanjisong_list.json")
            
            # Test detail page scraping for first project
            if projects:
                logger.info(f"\nTesting detail page scraping for: {projects[0]['title']}")
                details = await scraper.scrape_detail_page(projects[0])
                
                if details:
                    logger.info("\nProject details:")
                    for key, value in details.items():
                        logger.info(f"  {key}: {value}")
                    
                    # Save detail page results
                    with open(output_dir / "yuanjisong_detail.json", "w", encoding="utf-8") as f:
                        json.dump(details, f, ensure_ascii=False, indent=2)
                    logger.info("\nSaved detail page results to yuanjisong_detail.json")
                else:
                    logger.error("Failed to get project details")
        else:
            logger.error("No projects found on list page")
            
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_yuanjisong()) 