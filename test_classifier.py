"""
Test script for job classification analysis.
"""

import asyncio
from loguru import logger
from src.config.config import Config
from src.models.job_classifier import JobClassifier

async def test_classification():
    """Test job classification analysis."""
    try:
        # Initialize config and classifier
        config = Config()
        classifier = JobClassifier(config)
        
        # Run analysis
        logger.info("Starting job classification analysis...")
        results = await classifier.analyze()
        
        # Print summary
        logger.info("\nClassification Results:")
        for label, stats in results['summary'].items():
            logger.info(f"\nCategory: {label}")
            logger.info(f"Number of jobs: {stats['size']}")
            logger.info(f"Average price: ¥{stats['avg_price']:.2f}")
            logger.info(f"Price range: ¥{stats['min_price']} - ¥{stats['max_price']}")
            logger.info("Sample titles:")
            for title in stats['sample_titles']:
                logger.info(f"  - {title}")
                
        logger.info("\nAnalysis complete! Check the output directory for detailed results and visualizations.")
        
    except Exception as e:
        logger.error(f"Error during classification: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_classification()) 