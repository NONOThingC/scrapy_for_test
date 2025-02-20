import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://www.yuanjisong.com/job/allcity/page1")
        print(result.html)

if __name__ == "__main__":
    asyncio.run(main())