import asyncio
from src.config.config import Config
from src.scrapers.yuanjisong_scraper import YuanjisongScraper
from loguru import logger

async def test_detail_scraping():
    """Test detail page scraping functionality."""
    # Initialize config and scraper
    config = Config()
    scraper = YuanjisongScraper(config)
    
    # Test URL
    test_url = "https://www.yuanjisong.com/job/157239"
    
    logger.info(f"Testing detail page scraping for {test_url}")
    
    # Create a test project dict
    test_project = {"url": test_url, "title": "STM32软件开发"}
    
    # Get proxy configuration
    proxy = config.get_proxy()
    if proxy:
        logger.info(f"Using proxy: {proxy.get('http')}")
    
    # Try to scrape the detail page
    try:
        result = await scraper._scrape_detail_page(test_project, proxy)
        
        if result:
            logger.info("Successfully scraped detail page:")
            for key, value in result.items():
                logger.info(f"{key}: {value}")
            return result
        else:
            logger.error("Failed to scrape detail page")
            return None
            
    except Exception as e:
        logger.error(f"Error scraping detail page: {str(e)}")
        return None
    finally:
        # Ensure all resources are cleaned up
        await scraper.cleanup()

if __name__ == "__main__":
    try:
        # Run the test in the event loop
        asyncio.run(test_detail_scraping())
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
    # No need to manually handle event loop cleanup as asyncio.run() does this for us 