"""
Scraper implementation for yuanjisong.com.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urljoin
import logging

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
        url = 'https://www.yuanjisong.com' + url
        
    return url

class YuanjisongScraper(BaseScraper):
    """Scraper for yuanjisong.com."""

    def __init__(self, config: Config):
        """Initialize the scraper with config.
        
        Args:
            config (Config): Configuration object
        """
        super().__init__("yuanjisong", config.output_dir)
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
            wait_for=".div_bg_color_fff",  # Wait for job listings container
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
            wait_for=".consultant_title",  # Wait for job detail container
            js_code="""
                // Scroll through the page to ensure all content is loaded
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(r => setTimeout(r, 1000));
                window.scrollTo(0, 0);
            """
        )
        
        self.base_url = 'https://www.yuanjisong.com'
        
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

    def extract_project_links(self, html_content):
        """Extract project links and basic info from the list page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        project_containers = soup.find_all('div', class_='div_bg_color_fff div_padding_1 hover1 margin_bottom_1')
        self.logger.debug(f"Found {len(project_containers)} project containers")
        
        projects = []
        for container in project_containers:
            try:
                project = {}
                
                # Extract title and URL from the first <a> tag containing an <h4>
                title_link = container.find('a', href=lambda x: x and '/job/' in x)
                if title_link:
                    project['url'] = clean_url(title_link['href'])
                    title_elem = title_link.find('b')
                    if title_elem:
                        project['title'] = title_elem.text.strip()
                
                # Extract description from the <p> with margin_bottom_10 class
                desc_elem = container.find('p', class_='margin_bottom_10')
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if '描述：' in desc_text:
                        project['description'] = desc_text.split('描述：', 1)[1].strip()
                
                # Extract duration from the <p> containing glyphicon-time
                duration_elem = container.find('span', class_='glyphicon-time')
                if duration_elem:
                    duration_p = duration_elem.find_parent('p')
                    if duration_p:
                        duration_text = duration_p.get_text(strip=True)
                        if '工时：' in duration_text:
                            project['duration'] = duration_text.split('工时：', 1)[1].strip()
                
                # Extract price from the span with rixin-text-jobs class
                price_elem = container.find('span', class_='rixin-text-jobs')
                if price_elem:
                    try:
                        project['price'] = int(price_elem.text.strip())
                    except (ValueError, AttributeError):
                        project['price'] = 0
                
                # Extract applicants count from the i_post_num element
                applicants_elem = container.find('i', class_='i_post_num')
                if applicants_elem:
                    try:
                        project['applicants'] = int(applicants_elem.text.strip())
                    except (ValueError, AttributeError):
                        project['applicants'] = 0
                
                # Extract employer info from the employer link
                employer_link = container.find('a', href=lambda x: x and '/employer/' in x)
                if employer_link:
                    project['employer_url'] = clean_url(employer_link['href'])
                    employer_name = employer_link.find('span')
                    if employer_name:
                        project['employer_name'] = employer_name.text.strip()
                
                # Only append if we have the minimum required fields
                if all(key in project for key in ['url', 'title']):
                    projects.append(project)
                    self.logger.debug(f"Extracted project: {json.dumps(project, ensure_ascii=False)}")
                
            except Exception as e:
                self.logger.error(f"Error extracting project: {str(e)}")
                continue
        
        self.logger.info(f"Found {len(projects)} projects on page 1")
        if projects:
            self.logger.debug(f"First project details: {json.dumps(projects[0], ensure_ascii=False, indent=2)}")
        
        return projects

    def extract_project_details(self, html):
        """Extract project details from HTML content."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_elem = soup.select_one('h2')
            title = title_elem.text.strip() if title_elem else None
            
            # Extract basic info
            details = {}
            details['title'] = title
            
            # Find all basic info rows
            basic_info_rows = soup.select('.basic_info_row')
            for row in basic_info_rows:
                label_elem = row.select_one('.font_color_3')
                if not label_elem:
                    continue
                    
                label = label_elem.text.strip().rstrip('：')
                value = row.select_one('li:last-child')
                if not value:
                    continue
                    
                value_text = value.text.strip()
                
                if '合作方式' in label:
                    details['cooperation_type'] = value_text
                elif '预估日薪' in label:
                    details['daily_salary'] = int(''.join(filter(str.isdigit, value_text)))
                elif '预估总价' in label:
                    details['total_price'] = int(''.join(filter(str.isdigit, value_text)))
                elif '预估工时' in label:
                    details['duration'] = int(''.join(filter(str.isdigit, value_text)))
                elif '所在区域' in label:
                    details['location'] = value_text
            
            # Extract description
            desc_elem = soup.select_one('.mobmid p')
            if desc_elem:
                details['description'] = desc_elem.text.strip()
            
            # Extract employer credit info
            try:
                credit_list = soup.select('.admin-content-list li span a')
                if len(credit_list) >= 3:
                    details['employer_projects'] = int(credit_list[0].text.strip())
                    details['employer_reviews'] = int(credit_list[1].text.strip())
                    details['employer_complaints'] = int(credit_list[2].text.strip())
            except (ValueError, AttributeError, IndexError) as e:
                self.logger.warning(f"Failed to extract employer credit info: {str(e)}")
                details['employer_projects'] = 0
                details['employer_reviews'] = 0
                details['employer_complaints'] = 0
            
            self.logger.debug(f"Extracted project details: {details}")
            return details
            
        except Exception as e:
            self.logger.error(f"Error extracting project details: {str(e)}")
            return {}

    async def scrape_list_page(self, page: int) -> List[Dict]:
        """Scrape a list page to get job listings.
        
        Args:
            page (int): Page number
            
        Returns:
            List[Dict]: List of job listings
        """
        url = self.config.yuanjisong_url.format(page)
        logger.info(f"Scraping list page {url}")
        
        max_retries = self.config.max_retries
        for attempt in range(max_retries):
            try:
                async with AsyncWebCrawler() as crawler:
                    # Get crawler config
                    config = CrawlerRunConfig(
                        **self.config.get_crawler_config(
                            wait_for=".div_bg_color_fff",
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
                        logger.info(f"Using proxy: {proxy.get('http')}")
                    else:
                        logger.warning("No proxy available")
                    
                    result = await crawler.arun(url, config=config, proxy=proxy)
                    
                    if not result.success:
                        logger.error(f"Failed to fetch list page {url}: {result.error_message}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                            await asyncio.sleep(self.config.retry_delay)
                            continue
                        return []
                    
                    if not result.html:
                        logger.warning(f"No HTML content in list page {url}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                            await asyncio.sleep(self.config.retry_delay)
                            continue
                        return []
                    
                    # Log the first 1000 characters of HTML for debugging
                    if self.config.debug:
                        logger.debug(f"First 1000 chars of HTML:\n{result.html[:1000]}")
                    
                    # Extract project links and metadata
                    projects = self.extract_project_links(result.html)
                    logger.info(f"Found {len(projects)} projects on page {page}")
                    
                    # Check if we've reached the last page
                    if not projects:
                        logger.info(f"No more projects found on page {page}")
                        return []
                    
                    return projects
                    
            except Exception as e:
                logger.error(f"Error scraping list page {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                    await asyncio.sleep(self.config.retry_delay)
                    continue
        
        return []

    async def scrape_detail_page(self, project: Dict) -> Optional[Dict]:
        """Scrape a project detail page.
        
        Args:
            project (Dict): Project metadata from list page
            
        Returns:
            Optional[Dict]: Complete project details if successful
        """
        url = project['url']
        logger.info(f"Scraping detail page: {project['title']} ({url})")
        
        async with AsyncWebCrawler() as crawler:
            # Get crawler config with proxy
            config = CrawlerRunConfig(
                **self.config.get_crawler_config(
                    wait_for=".consultant_title",
                    js_code="""
                        // Scroll through the page to ensure all content is loaded
                        window.scrollTo(0, document.body.scrollHeight);
                        await new Promise(r => setTimeout(r, 1000));
                        window.scrollTo(0, 0);
                    """
                )
            )
            
            # Get proxy configuration
            proxy = self.config.get_proxy()
            if proxy:
                logger.info(f"Using proxy: {proxy.get('http')}")
            else:
                logger.warning("No proxy available")
            
            result = await crawler.arun(url, config=config, proxy=proxy)
            
            if not result.success:
                logger.error(f"Failed to fetch detail page {url}: {result.error_message}")
                return None
            
            if not result.html:
                logger.warning(f"No HTML content in detail page {url}")
                return None
            
            # Extract detailed project information
            details = self.extract_project_details(result.html)
            
            # Merge with list page metadata
            merged = {**project, **details}
            
            # Ensure we have the most important fields
            if not merged.get('title') or not merged.get('url'):
                logger.warning(f"Missing required fields for {url}")
                return None
            
            return merged

    async def scrape_page(self, page: int = 1) -> List[Dict]:
        """Scrape a single page of job listings.
        
        Args:
            page (int): Page number to scrape
            
        Returns:
            List[Dict]: List of scraped job listings
        """
        self.logger.info(f"Scraping page {page} from yuanjisong.com")
        
        detailed_projects = []
        
        try:
            # Initialize crawler for list page
            async with AsyncWebCrawler() as crawler:
                # Get crawler config with proxy
                config = CrawlerRunConfig(
                    **self.config.get_crawler_config(
                        wait_for=".div_bg_color_fff",
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
                url = f"https://www.yuanjisong.com/job/allcity/page{page}"
                result = await crawler.arun(url, config=config, proxy=proxy)
                
                if not result or not result.html:
                    self.logger.error(f"Failed to scrape page {page}")
                    return []
                    
                # Extract project links and basic info
                projects = self.extract_project_links(result.html)
                self.logger.info(f"Found {len(projects)} projects on page {page}")
            
            # Create tasks for detail page scraping
            detail_tasks = []
            for project in projects:
                task = asyncio.create_task(self._scrape_detail_page(project, proxy))
                detail_tasks.append(task)
            
            # Wait for all detail pages to be scraped with timeout
            try:
                # Use asyncio.gather to collect all results
                completed_tasks = await asyncio.wait_for(
                    asyncio.gather(*detail_tasks, return_exceptions=True),
                    timeout=len(projects) * 10  # 10 seconds per project
                )
                
                # Process results
                for result in completed_tasks:
                    if isinstance(result, Exception):
                        self.logger.error(f"Error in detail scraping: {str(result)}")
                    elif result:
                        detailed_projects.append(result)
                
            except asyncio.TimeoutError:
                self.logger.error("Timeout waiting for detail pages")
                # Add basic info for projects that didn't complete
                for project in projects:
                    if not any(d.get('url') == project['url'] for d in detailed_projects):
                        detailed_projects.append(project)
                
        except Exception as e:
            self.logger.error(f"Error scraping page {page}: {str(e)}")
            return []
            
        # Save results for this page
        self.save_results(detailed_projects)
        
        return detailed_projects

    async def _scrape_detail_page(self, project: Dict, proxy: Optional[Dict] = None) -> Optional[Dict]:
        """Scrape a single detail page.
        
        Args:
            project (Dict): Project basic info
            proxy (Optional[Dict]): Proxy configuration
            
        Returns:
            Optional[Dict]: Project with details if successful
        """
        html_content = None  # Store HTML content outside the crawler context
        
        try:
            async with AsyncWebCrawler() as detail_crawler:
                # Configure crawler for detail page
                detail_config = CrawlerRunConfig(
                    **self.config.get_crawler_config(
                        wait_for="h2",  # Updated selector
                        js_code="""
                            // Scroll through the page to ensure all content is loaded
                            window.scrollTo(0, document.body.scrollHeight);
                            await new Promise(r => setTimeout(r, 1000));
                            window.scrollTo(0, 0);
                            // Wait for content to stabilize
                            await new Promise(r => setTimeout(r, 500));
                        """
                    )
                )
                
                # Add timeout for detail page scraping
                detail_result = await asyncio.wait_for(
                    detail_crawler.arun(project['url'], config=detail_config, proxy=proxy),
                    timeout=30  # 30 seconds timeout
                )
                
                if detail_result and detail_result.success:
                    html_content = detail_result.html
                    self.logger.debug(f"Successfully fetched HTML for {project['url']}")
                else:
                    self.logger.warning(f"Failed to fetch detail page: {project['url']}")
                    return project  # Return basic info if fetch fails
            
            # Process HTML content outside the crawler context
            if html_content:
                # Extract details and merge with basic info
                details = self.extract_project_details(html_content)
                if details:
                    project.update(details)
                    self.logger.debug(f"Added details for project: {project['url']}")
                    return project
            
            self.logger.warning(f"No valid HTML content for: {project['url']}")
            return project  # Return basic info if content processing fails
                
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.error(f"Error scraping detail page {project['url']}: {str(e)}")
            return project  # Return basic info on error

    async def scrape(self, max_pages: int = 5) -> List[Dict]:
        """Scrape job listings from yuanjisong.com using two-stage scraping.

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
                # Scrape one page at a time
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
        
        # Save final results
        output_file = Path(self.config.output_dir) / f"{self.platform_name}.json"
        logger.info(f"Saving {len(all_jobs)} jobs to {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_jobs, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved results to {output_file}")
        except Exception as e:
            logger.error(f"Error saving results to {output_file}: {str(e)}")
        
        return all_jobs

    async def cleanup(self):
        """Clean up resources used by the scraper."""
        try:
            # Add any cleanup code here if needed in the future
            pass
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}") 