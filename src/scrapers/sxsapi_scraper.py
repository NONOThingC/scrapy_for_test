"""
Scraper implementation for sxsapi.com.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import asyncio

from src.config.config import Config
from src.scrapers.base_scraper import BaseScraper
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

def clean_url(url: str) -> str:
    """Clean up URL by removing artifacts and normalizing format.
    
    Args:
        url (str): Raw URL from markdown
        
    Returns:
        str: Cleaned URL
    """
    # Remove </> artifacts and any text after space
    url = url.split()[0].replace('</', '').replace('>', '')
    
    # Remove javascript: links
    if 'javascript:' in url:
        return ''
        
    # Ensure proper domain
    if not url.startswith('http'):
        url = 'https://sxsapi.com' + url
        
    return url

class SxsapiScraper(BaseScraper):
    """Scraper for sxsapi.com."""

    def __init__(self, config: Config):
        """Initialize the scraper with config.
        
        Args:
            config (Config): Configuration object
        """
        super().__init__("sxsapi", config.output_dir)
        self.config = config
        self.logger = logger
        
        # Configure crawler for list page
        self.list_config = CrawlerRunConfig(
            verbose=True,
            word_count_threshold=config.word_count_threshold,
            excluded_tags=config.excluded_tags,
            page_timeout=config.page_timeout,
            simulate_user=config.simulate_user,
            magic=config.magic,
            wait_for=".project-list, .project-grid, .job-list",  # Wait for job listings container
            js_code="""
                // Scroll to bottom to trigger any lazy loading
                window.scrollTo(0, document.body.scrollHeight);
                // Wait a bit for content to load
                await new Promise(r => setTimeout(r, 2000));
                // Scroll back to top
                window.scrollTo(0, 0);
            """
        )
        
        # Configure crawler for detail page
        self.detail_config = CrawlerRunConfig(
            verbose=True,
            word_count_threshold=config.word_count_threshold,
            excluded_tags=config.excluded_tags,
            page_timeout=config.page_timeout,
            simulate_user=config.simulate_user,
            magic=config.magic,
            wait_for="main, article, .content, .container",  # More general selectors
            js_code="""
                // Scroll through the page to ensure all content is loaded
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(r => setTimeout(r, 1000));
                window.scrollTo(0, 0);
            """
        )
        
        self.base_url = 'https://sxsapi.com'
        
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

    async def scrape_page(self, page: int = 1) -> List[Dict]:
        """Scrape a single page of job listings.
        
        Args:
            page (int): Page number to scrape
            
        Returns:
            List[Dict]: List of scraped job listings
        """
        self.logger.info(f"Scraping page {page} from sxsapi.com")
        
        # Initialize crawler
        async with AsyncWebCrawler() as crawler:
            # Get crawler config with proxy
            config = CrawlerRunConfig(
                **self.config.get_crawler_config(
                    wait_for=".project-list, .project-grid, .job-list",
                    js_code="""
                        // Scroll to bottom to trigger any lazy loading
                        window.scrollTo(0, document.body.scrollHeight);
                        // Wait a bit for content to load
                        await new Promise(r => setTimeout(r, 2000));
                        // Scroll back to top
                        window.scrollTo(0, 0);
                    """
                )
            )
            
            # Get proxy configuration
            proxy = self.config.get_proxy()
            if proxy:
                self.logger.info(f"Using proxy: {proxy.get('http')}")
            else:
                self.logger.warning("No proxy available")
            
            # Scrape list page
            url = f"https://sxsapi.com/?pageNo={page}"
            result = await crawler.arun(url, config=config, proxy=proxy)
            
            if not result or not result.markdown:
                self.logger.error(f"Failed to scrape page {page}")
                return []
                
            # Extract project links and basic info
            projects = self.extract_project_links(result.markdown)
            self.logger.info(f"Found {len(projects)} projects on page {page}")
            
            # Scrape detail pages
            detailed_projects = []
            for project in projects:
                try:
                    # Configure crawler for detail page
                    detail_config = CrawlerRunConfig(
                        **self.config.get_crawler_config(
                            wait_for="main, article, .content, .container",
                            js_code="""
                                // Scroll through the page to ensure all content is loaded
                                window.scrollTo(0, document.body.scrollHeight);
                                await new Promise(r => setTimeout(r, 1000));
                                window.scrollTo(0, 0);
                            """
                        )
                    )
                    
                    # Scrape detail page
                    detail_result = await crawler.arun(project['url'], config=detail_config, proxy=proxy)
                    if detail_result and detail_result.markdown:
                        # Extract details and merge with basic info
                        details = self.extract_project_details(detail_result.markdown)
                        if details:
                            project.update(details)
                            detailed_projects.append(project)
                            self.logger.debug(f"Added details for project: {project['url']}")
                    else:
                        self.logger.warning(f"Failed to scrape detail page: {project['url']}")
                        detailed_projects.append(project)  # Add basic info even if detail scraping fails
                        
                except Exception as e:
                    self.logger.error(f"Error scraping detail page {project['url']}: {str(e)}")
                    detailed_projects.append(project)  # Add basic info even if detail scraping fails
                    
            # Save results for this page
            self.save_results(detailed_projects)
            
            return detailed_projects

    def extract_project_links(self, markdown: str) -> List[Dict[str, str]]:
        """Extract project links from markdown content.
        
        Args:
            markdown (str): Markdown content
            
        Returns:
            List[Dict[str, str]]: List of project URLs and titles
        """
        projects = []
        current_project = {}
        
        for line in markdown.split('\n'):
            line = line.strip()
            
            # Skip empty lines and navigation links
            if not line or any(x in line.lower() for x in ['登录', '注册', '会员', '友链合作']):
                continue
                
            # Look for project title and link
            # Format: ##  [ 项目标题 ](https://sxsapi.com/</post/235>) ￥ 预算
            title_match = re.search(r'##\s*\[\s*([^\]]+)\s*\]\s*\((https?://[^)]+/post/\d+[^)]*)\)\s*￥\s*([\d~万千以上以下待商议]+)', line)
            if title_match:
                if current_project:
                    projects.append(current_project)
                current_project = {
                    'title': title_match.group(1).strip(),
                    'url': clean_url(title_match.group(2)),
                    'price': title_match.group(3).strip()
                }
                continue
                
            # Look for duration
            duration_match = re.search(r'\*\s*(\d+天|商议工期)', line)
            if duration_match and current_project:
                current_project['duration'] = duration_match.group(1)
                continue
                
            # Look for deadline
            deadline_match = re.search(r'\*\s*竞标截止：(\d{4}-\d{2}-\d{2})', line)
            if deadline_match and current_project:
                current_project['deadline'] = deadline_match.group(1)
                
        # Add last project if exists
        if current_project:
            projects.append(current_project)
            
        return projects

    def extract_project_details(self, markdown: str) -> Dict:
        """Extract project details from markdown content.
        
        Args:
            markdown (str): Markdown content
            
        Returns:
            Dict: Project details
        """
        details = {}
        
        # Extract title (format: # 项目标题)
        title_match = re.search(r'#\s*([^#\n]+?)(?:\s*￥|$)', markdown)
        if title_match:
            details['title'] = title_match.group(1).strip()
        
        # Extract price (format: ￥ 5千~1万)
        price_match = re.search(r'￥\s*([\d~万千以上以下待商议]+)', markdown)
        if price_match:
            details['price'] = price_match.group(1).strip()
        
        # Extract duration (format: 工期：30天 or 工期要求：30天)
        duration_match = re.search(r'工期[：要求]*：\s*(\d+天|商议工期)', markdown)
        if duration_match:
            details['duration'] = duration_match.group(1)
        
        # Extract deadline (format: 竞标截止：2025-03-05)
        deadline_match = re.search(r'竞标截止：(\d{4}-\d{2}-\d{2})', markdown)
        if deadline_match:
            details['deadline'] = deadline_match.group(1)
        
        # Extract description
        description = ""
        description_started = False
        for line in markdown.split('\n'):
            line = line.strip()
            
            # Start collecting description after "项目描述"
            if '项目描述' in line:
                description_started = True
                continue
                
            # Stop at certain markers
            if description_started:
                if any(x in line for x in ['附件', '报名列表', '阅读全部', '开发者工作指南']):
                    break
                if line and not line.startswith('#') and not line.startswith('!['):
                    description += line + ' '
        
        if description:
            details['description'] = description.strip()
            
        # Extract skills (format: 技能要求：xxx)
        skills_match = re.search(r'技能要求：([^\n]+)', markdown)
        if skills_match:
            details['skills'] = skills_match.group(1).strip()
            
        # Extract cooperation preference (format: 合作倾向：xxx)
        coop_match = re.search(r'合作倾向：([^\n]+)', markdown)
        if coop_match:
            details['cooperation'] = coop_match.group(1).strip()
        
        return details 

    async def scrape(self, max_pages: int = 5) -> List[Dict]:
        """Scrape job listings from sxsapi.com using two-stage scraping.

        Args:
            max_pages (int, optional): Maximum number of pages to scrape. Defaults to 5.
                                     Set to 0 for unlimited pages.

        Returns:
            List[Dict]: List of scraped job listings
        """
        all_jobs = []
        page = 1
        
        while True:
            try:
                # Stage 1: Get job listings from list page
                projects = await self.scrape_page(page)
                if not projects:
                    logger.warning(f"No projects found on page {page}, stopping pagination")
                    break
                
                # Add projects to results
                all_jobs.extend(projects)
                logger.info(f"Added {len(projects)} projects from page {page}")
                
                # Check if we've reached max_pages
                if max_pages and page >= max_pages:
                    logger.info(f"Reached max pages limit ({max_pages})")
                    break
                    
                # Increment page counter
                page += 1
                
                # Add delay between pages
                await asyncio.sleep(self.config.rate_limit)
                        
            except Exception as e:
                logger.error(f"Error scraping list page {page}: {str(e)}")
                break
        
        # Save results
        output_file = Path(self.config.output_dir) / f"{self.platform_name}.json"
        logger.info(f"Saving {len(all_jobs)} jobs to {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_jobs, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved results to {output_file}")
        except Exception as e:
            logger.error(f"Error saving results to {output_file}: {str(e)}")
        
        return all_jobs 