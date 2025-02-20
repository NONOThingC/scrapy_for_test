"""
Setup script for the job scraper package.
"""
from setuptools import setup, find_packages

setup(
    name="job_scraper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.9.3",
        "requests>=2.25.1",
        "pandas>=1.2.0",
        "scikit-learn>=0.24.0",
        "matplotlib>=3.3.0",
        "seaborn>=0.11.0",
        "python-dotenv>=0.19.0",
        "loguru>=0.5.3",
        "aiohttp>=3.8.0",
        "asyncio>=3.4.3",
        "numpy>=1.19.0",
        "playwright>=1.49.0"
    ],
    python_requires=">=3.8",
) 