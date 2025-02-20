"""
Proxy configuration for web scraping.
"""
from typing import Dict, Optional, List
import random
import requests
import time
from loguru import logger

class ProxyConfig:
    """Proxy configuration class."""
    
    def __init__(self):
        """Initialize proxy configuration."""
        # Proxy API configuration
        self.api_url = "http://api.xiaoxiangdaili.com/ip/get"  # Changed to HTTP
        self.api_params = {
            "appKey": "1208088376956571648",
            "appSecret": "RGxk8zzg",
            "cnt": "2",  # Request 2 proxies at once
            "wt": "text",  # Changed to text format as per API docs
            "method": "http"  # Changed to HTTP
        }
        
        # Cache for proxy IPs and expiration time
        self.proxy_pool = []  # List of available proxies
        self.last_request_time = 0  # Last time we requested new proxies
        self.request_interval = 60  # Minimum seconds between API requests
        
        # Default proxy settings
        self.default_proxy = None
        
        # Enable/disable proxy
        self.enabled = True
        
        logger.info("Initialized proxy configuration")
        
    def _fetch_new_proxy(self) -> Optional[str]:
        """Fetch new proxies from the API and add them to the pool.
        
        Returns:
            Optional[str]: First proxy URL if successful, None otherwise
        """
        if not self.enabled:
            logger.info("Proxy is disabled, returning None")
            return None
            
        current_time = time.time()
        if current_time - self.last_request_time < self.request_interval:
            logger.warning(f"Too soon to request new proxies. Please wait {self.request_interval - (current_time - self.last_request_time):.1f} seconds")
            # Try to use existing proxy from pool
            if self.proxy_pool:
                proxy = random.choice(self.proxy_pool)
                logger.info(f"Using existing proxy from pool: {proxy}")
                return proxy
            return None
            
        try:
            logger.debug(f"Fetching new proxies from: {self.api_url}")
            response = requests.get(self.api_url, params=self.api_params, timeout=10)
            
            if response.status_code == 200:
                # API returns one or more IP:PORT in text format, one per line
                proxy_list = response.text.strip().split('\n')
                logger.debug(f"API response: {proxy_list}")
                
                # Clear old proxies
                self.proxy_pool.clear()
                
                for proxy_text in proxy_list:
                    if proxy_text and ':' in proxy_text:
                        # Construct proxy URL with authentication and HTTP
                        proxy_meta = f"http://{self.api_params['appKey']}:{self.api_params['appSecret']}@{proxy_text}"
                        self.proxy_pool.append(proxy_meta)
                        logger.info(f"Added proxy to pool: {proxy_meta}")
                
                if self.proxy_pool:
                    self.last_request_time = current_time
                    return random.choice(self.proxy_pool)
                    
                logger.error(f"No valid proxies in response: {proxy_list}")
                return None
                
            logger.error(f"Proxy API returned status code: {response.status_code}")
            return None
                
        except Exception as e:
            logger.error(f"Error fetching proxies: {str(e)}")
            return None
        
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get a proxy configuration.
        
        Returns:
            Optional[Dict[str, str]]: Proxy configuration or None
        """
        if not self.enabled:
            logger.info("Proxy is disabled, returning None")
            return None
            
        # Try to get a proxy from the pool first
        if self.proxy_pool:
            proxy = random.choice(self.proxy_pool)
            logger.debug(f"Using proxy from pool: {proxy}")
            return {"http": proxy}
            
        # If pool is empty, try to fetch new proxies
        proxy = self._fetch_new_proxy()
        if proxy:
            return {"http": proxy}
            
        # If still no proxies available, use default proxy
        if self.default_proxy:
            logger.info(f"Using default proxy: {self.default_proxy}")
            return {"http": self.default_proxy}
            
        logger.warning("No proxy available")
        return None
        
    def add_proxy(self, proxy: str):
        """Add a proxy to use as fallback.
        
        Args:
            proxy (str): Proxy URL
        """
        self.default_proxy = proxy
        logger.info(f"Added default proxy: {proxy}")
            
    def set_default_proxy(self, proxy: str):
        """Set the default proxy as fallback.
        
        Args:
            proxy (str): Proxy URL
        """
        self.default_proxy = proxy
        logger.info(f"Set default proxy: {proxy}")
        
    def enable(self):
        """Enable proxy usage."""
        self.enabled = True
        logger.info("Proxy enabled")
        
    def disable(self):
        """Disable proxy usage."""
        self.enabled = False
        logger.info("Proxy disabled") 