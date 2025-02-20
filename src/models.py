"""
Data models for the project.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class FreelanceProject:
    """Represents a freelance project."""
    
    title: str
    description: str
    platform: str
    url: str
    price: Optional[str] = None
    published_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Post initialization processing."""
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the project to a dictionary."""
        data = asdict(self)
        
        # 转换日期时间为 ISO 格式字符串
        if self.published_at:
            data['published_at'] = self.published_at.isoformat()
        if self.deadline:
            data['deadline'] = self.deadline.isoformat()
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FreelanceProject':
        """Create a project from a dictionary."""
        # 转换日期时间字符串为 datetime 对象
        if 'published_at' in data and data['published_at']:
            data['published_at'] = datetime.fromisoformat(data['published_at'])
        if 'deadline' in data and data['deadline']:
            data['deadline'] = datetime.fromisoformat(data['deadline'])
            
        return cls(**data) 