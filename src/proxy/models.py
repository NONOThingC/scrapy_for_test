"""
Proxy models for the project.
"""

from dataclasses import dataclass, field
from typing import Set
from datetime import datetime

@dataclass
class Proxy:
    """Represents a proxy server."""
    
    host: str
    port: int
    protocol: str = 'http'  # 默认协议
    username: str = None
    password: str = None
    last_checked: datetime = None
    is_valid: bool = False
    response_time: float = float('inf')
    fail_count: int = 0
    working_protocols: Set[str] = field(default_factory=set)
    
    @property
    def url(self) -> str:
        """Get the proxy URL."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def get_url_with_protocol(self, protocol: str) -> str:
        """Get the proxy URL with a specific protocol."""
        if self.username and self.password:
            return f"{protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{protocol}://{self.host}:{self.port}"
    
    def add_working_protocol(self, protocol: str):
        """Add a working protocol."""
        self.working_protocols.add(protocol)
    
    def update_status(self, is_valid: bool, response_time: float = None):
        """Update proxy status."""
        self.is_valid = is_valid
        self.last_checked = datetime.now()
        
        if is_valid:
            if response_time is not None:
                self.response_time = response_time
            self.fail_count = 0
        else:
            self.fail_count += 1 