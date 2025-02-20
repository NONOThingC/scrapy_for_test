"""
Test script to verify imports are working correctly.
"""
from loguru import logger

from src.config.config import YUANJISONG_URL, SXSAPI_URL
from src.scrapers.yuanjisong_scraper import YuanjisongScraper
from src.scrapers.sxsapi_scraper import SxsapiScraper


def test_imports():
    """Test that all necessary imports are working."""
    logger.info("Testing imports...")
    
    # Test config imports
    logger.info(f"YUANJISONG_URL: {YUANJISONG_URL}")
    logger.info(f"SXSAPI_URL: {SXSAPI_URL}")
    
    # Test scraper imports
    yuanjisong = YuanjisongScraper()
    sxsapi = SxsapiScraper()
    
    logger.info("All imports successful!")


if __name__ == "__main__":
    test_imports() 