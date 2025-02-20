"""
Test script for running proxy pool and scraper.
"""

import asyncio
import logging
from src.proxy.proxy_pool import ProxyPool
from src.scrapers.yuanjisong_scraper import YuanjisongScraper
from src.utils.logger import setup_logger

logger = setup_logger('test_proxy_scraper')

async def main():
    """Main function to test proxy pool and scraper."""
    try:
        # 初始化代理池
        logger.info("Initializing proxy pool...")
        async with ProxyPool() as pool:
            # 等待代理池填充
            logger.info("Waiting for proxy pool to be populated...")
            await asyncio.sleep(5)  # 给代理池一些时间来获取和验证代理
            
            # 创建爬虫实例
            logger.info("Creating scraper instance...")
            scraper = YuanjisongScraper(use_proxy=True)
            
            # 运行爬虫
            logger.info("Starting scraper...")
            projects = await scraper.scrape()
            
            # 输出结果
            logger.info(f"Total projects scraped: {len(projects)}")
            for project in projects:
                logger.info("-" * 80)
                logger.info(f"Title: {project.title}")
                logger.info(f"URL: {project.url}")
                logger.info(f"Price: {project.price}")
                logger.info(f"Description: {project.description[:200]}...")
                if project.metadata:
                    logger.info("Metadata:")
                    for key, value in project.metadata.items():
                        logger.info(f"  {key}: {value}")
                        
    except Exception as e:
        logger.error(f"Error running proxy scraper: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main()) 