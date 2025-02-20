"""
OSCHINA API analyzer using Selenium.
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import json
from typing import List, Dict, Any, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OSChinaAPIAnalyzer:
    """Analyzer for OSCHINA API using Selenium."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.base_url = 'https://zb.oschina.net/projects/list.html'
        self.setup_driver()
        
    def setup_driver(self):
        """Setup Chrome WebDriver with necessary options."""
        try:
            chrome_options = Options()
            # 添加必要的 Chrome 选项
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--ignore-certificate-errors')  # 忽略证书错误
            chrome_options.add_argument('--ignore-ssl-errors')  # 忽略 SSL 错误
            
            # 启用性能日志记录
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # 设置用户代理
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
            
            # 使用 webdriver_manager 安装和管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver 初始化成功")
            
        except Exception as e:
            logger.error(f"设置 Chrome WebDriver 时出错: {e}")
            raise
        
    def analyze_network_requests(self) -> List[Dict[str, Any]]:
        """Analyze network requests to find API endpoints."""
        api_requests = []
        
        try:
            # 访问目标页面
            logger.info(f"访问页面: {self.base_url}")
            self.driver.get(self.base_url)
            
            # 等待页面加载
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                logger.warning("页面加载超时，继续执行...")
            
            # 获取性能日志
            logs = self.driver.get_log('performance')
            logger.info(f"获取到 {len(logs)} 条性能日志")
            
            # 分析网络请求
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    if (
                        'Network.requestWillBeSent' in log['method']
                        and 'request' in log['params']
                    ):
                        request = log['params']['request']
                        url = request.get('url', '')
                        
                        # 只关注 API 请求
                        if 'api' in url.lower() and 'zb.oschina.net' in url:
                            api_info = {
                                'url': url,
                                'method': request.get('method', ''),
                                'headers': request.get('headers', {}),
                                'timestamp': entry['timestamp']
                            }
                            api_requests.append(api_info)
                            logger.info(f"发现 API 请求: {url}")
                            
                except Exception as e:
                    logger.error(f"解析日志条目时出错: {e}")
                    continue
                    
        except WebDriverException as e:
            logger.error(f"WebDriver 错误: {e}")
        except Exception as e:
            logger.error(f"分析网络请求时出错: {e}")
        
        return api_requests
    
    def get_page_source(self) -> str:
        """Get the current page source."""
        return self.driver.page_source
    
    def analyze_xhr_requests(self) -> List[Dict[str, Any]]:
        """Analyze XHR requests specifically."""
        xhr_requests = []
        
        try:
            # 清除现有日志
            self.driver.get_log('performance')
            
            # 点击分页按钮触发新的请求
            try:
                next_page = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.pagination .next'))
                )
                next_page.click()
                time.sleep(2)  # 等待请求完成
            except TimeoutException:
                logger.warning("未找到分页按钮或等待超时")
            except Exception as e:
                logger.warning(f"点击下一页按钮时出错: {e}")
            
            # 获取新的性能日志
            logs = self.driver.get_log('performance')
            logger.info(f"获取到 {len(logs)} 条 XHR 性能日志")
            
            # 分析 XHR 请求
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    if (
                        'Network.requestWillBeSent' in log['method']
                        and 'request' in log['params']
                        and log['params'].get('type') == 'XHR'
                    ):
                        request = log['params']['request']
                        url = request.get('url', '')
                        
                        if 'api' in url.lower() and 'zb.oschina.net' in url:
                            xhr_info = {
                                'url': url,
                                'method': request.get('method', ''),
                                'headers': request.get('headers', {}),
                                'timestamp': entry['timestamp']
                            }
                            xhr_requests.append(xhr_info)
                            logger.info(f"发现 XHR 请求: {url}")
                            
                except Exception as e:
                    logger.error(f"解析 XHR 日志条目时出错: {e}")
                    continue
                    
        except WebDriverException as e:
            logger.error(f"WebDriver 错误: {e}")
        except Exception as e:
            logger.error(f"分析 XHR 请求时出错: {e}")
        
        return xhr_requests
    
    def close(self):
        """Close the WebDriver."""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                logger.info("WebDriver 已关闭")
            except Exception as e:
                logger.error(f"关闭 WebDriver 时出错: {e}")
            
    def __enter__(self):
        """Context manager enter."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

def main():
    """Main function to run the analyzer."""
    try:
        with OSChinaAPIAnalyzer() as analyzer:
            # 分析所有网络请求
            logger.info("开始分析网络请求...")
            api_requests = analyzer.analyze_network_requests()
            
            # 分析 XHR 请求
            logger.info("开始分析 XHR 请求...")
            xhr_requests = analyzer.analyze_xhr_requests()
            
            # 输出结果
            logger.info("\n=== API 请求分析结果 ===")
            for req in api_requests:
                logger.info(f"URL: {req['url']}")
                logger.info(f"Method: {req['method']}")
                logger.info("Headers:")
                for key, value in req['headers'].items():
                    logger.info(f"  {key}: {value}")
                logger.info("-" * 50)
            
            logger.info("\n=== XHR 请求分析结果 ===")
            for req in xhr_requests:
                logger.info(f"URL: {req['url']}")
                logger.info(f"Method: {req['method']}")
                logger.info("Headers:")
                for key, value in req['headers'].items():
                    logger.info(f"  {key}: {value}")
                logger.info("-" * 50)
                
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        raise

if __name__ == '__main__':
    main() 