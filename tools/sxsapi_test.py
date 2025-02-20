"""
Test script to examine sxsapi.com content using Crawl4AI.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict
from loguru import logger
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

def extract_project_links(markdown: str) -> List[Dict[str, str]]:
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

def extract_project_details(markdown: str) -> Dict:
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

async def test_sxsapi():
    """Test scraping sxsapi.com and examine its content."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Configure crawler for list page
    list_config = CrawlerRunConfig(
        verbose=True,
        word_count_threshold=10,
        excluded_tags=["nav", "footer"],
        js_code="document.querySelector('.show-more')?.click();",
        page_timeout=60000,
        simulate_user=True,
        magic=True,
        wait_for=".project-list, .project-grid, .job-list"
    )
    
    # Configure crawler for detail page
    detail_config = CrawlerRunConfig(
        verbose=True,
        word_count_threshold=10,
        excluded_tags=["nav", "footer"],
        page_timeout=60000,
        simulate_user=True,
        magic=True,
        wait_for="main, article, .content, .container"  # More general selectors
    )
    
    async with AsyncWebCrawler() as crawler:
        # Test list page
        logger.info("Testing list page...")
        try:
            result = await crawler.arun("https://sxsapi.com/?pageNo=1", config=list_config)
            
            if result.success:
                logger.info("Successfully fetched list page")
                
                if result.markdown:
                    # Extract project links
                    projects = extract_project_links(result.markdown)
                    logger.info(f"\nFound {len(projects)} projects:")
                    for project in projects:
                        logger.info(f"  - {project['title']}")
                        logger.info(f"    URL: {project['url']}")
                        logger.info(f"    Price: {project['price']}")
                        if 'duration' in project:
                            logger.info(f"    Duration: {project['duration']}")
                        if 'deadline' in project:
                            logger.info(f"    Deadline: {project['deadline']}")
                        logger.info("")
                    
                    # Save markdown for analysis
                    with open(output_dir / "sxsapi_list.md", "w", encoding="utf-8") as f:
                        f.write(result.markdown)
                    logger.info("Saved list page markdown")
                    
                    # Save extracted projects
                    with open(output_dir / "sxsapi_projects.json", "w", encoding="utf-8") as f:
                        json.dump(projects, f, ensure_ascii=False, indent=2)
                    logger.info("Saved projects to sxsapi_projects.json")
                    
                    # Test first project page
                    if projects:
                        logger.info(f"\nTesting project page: {projects[0]['title']}")
                        detail_result = await crawler.arun(projects[0]['url'], config=detail_config)
                        
                        if detail_result.success and detail_result.markdown:
                            # Extract and display project details
                            details = extract_project_details(detail_result.markdown)
                            logger.info("\nProject details:")
                            for key, value in details.items():
                                logger.info(f"  {key}: {value}")
                            
                            # Save project details
                            with open(output_dir / "sxsapi_project.json", "w", encoding="utf-8") as f:
                                json.dump(details, f, ensure_ascii=False, indent=2)
                            logger.info("\nSaved project details to sxsapi_project.json")
                            
                            # Save project page markdown
                            with open(output_dir / "sxsapi_project.md", "w", encoding="utf-8") as f:
                                f.write(detail_result.markdown)
                            logger.info("Saved project page markdown")
                        else:
                            logger.error(f"Failed to fetch project page: {detail_result.error_message if detail_result else 'No response'}")
                else:
                    logger.warning("No markdown content in list page response")
            else:
                logger.error(f"Failed to fetch list page: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_sxsapi())