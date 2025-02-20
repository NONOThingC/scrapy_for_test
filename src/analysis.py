"""
Script to analyze and visualize the scraped job listings data.
"""
import json
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from src.config.config import OUTPUT_DIR


def load_data() -> Dict[str, List[Dict]]:
    """Load scraped data from JSON files.

    Returns:
        Dict[str, List[Dict]]: Dictionary mapping platform names to their job listings
    """
    data = {}
    for file in OUTPUT_DIR.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data[file.stem] = json.load(f)
            logger.info(f"Loaded {len(data[file.stem])} listings from {file.name}")
        except Exception as e:
            logger.error(f"Error loading {file.name}: {e}")
    return data


def preprocess_text(text: str) -> str:
    """Preprocess text for analysis.

    Args:
        text (str): Input text

    Returns:
        str: Preprocessed text
    """
    if not text:
        return ""
    # Convert to lowercase and remove special characters
    text = text.lower()
    # Add more preprocessing steps as needed
    return text


def cluster_jobs(data: Dict[str, List[Dict]], n_clusters: int = 5) -> Dict[str, List[Dict]]:
    """Cluster job listings based on title and description.

    Args:
        data (Dict[str, List[Dict]]): Job listings data
        n_clusters (int, optional): Number of clusters. Defaults to 5.

    Returns:
        Dict[str, List[Dict]]: Job listings with cluster labels
    """
    # Combine all job listings
    all_jobs = []
    for platform, listings in data.items():
        for job in listings:
            if job['title'] and job['description']:
                combined_text = preprocess_text(job['title'] + " " + job['description'])
                all_jobs.append({
                    'platform': platform,
                    'text': combined_text,
                    'original': job
                })

    if not all_jobs:
        logger.error("No valid job listings found for clustering")
        return data

    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform([job['text'] for job in all_jobs])

    # Perform clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(X)

    # Add cluster labels to job listings
    for job, cluster in zip(all_jobs, clusters):
        job['original']['cluster'] = int(cluster)

    # Update original data with cluster labels
    clustered_data = {platform: [] for platform in data.keys()}
    for job in all_jobs:
        clustered_data[job['platform']].append(job['original'])

    return clustered_data


def analyze_prices(data: Dict[str, List[Dict]]) -> None:
    """Analyze and visualize price distributions by cluster.

    Args:
        data (Dict[str, List[Dict]]): Clustered job listings data
    """
    # Prepare data for visualization
    plot_data = []
    for platform, listings in data.items():
        for job in listings:
            if 'price' in job and job['price'] and 'cluster' in job:
                try:
                    # Extract numeric price value (adjust based on actual format)
                    price_str = job['price'].replace('¥', '').replace(',', '').strip()
                    price = float(price_str)
                    plot_data.append({
                        'platform': platform,
                        'cluster': f"Cluster {job['cluster']}",
                        'price': price
                    })
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not parse price '{job.get('price')}': {e}")

    if not plot_data:
        logger.error("No valid price data found for analysis")
        return

    # Create DataFrame
    df = pd.DataFrame(plot_data)

    # Set up the plot style
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Price distribution by cluster
    sns.boxplot(data=df, x='cluster', y='price', ax=axes[0])
    axes[0].set_title('Price Distribution by Cluster')
    axes[0].set_xlabel('Cluster')
    axes[0].set_ylabel('Price (¥)')
    axes[0].tick_params(axis='x', rotation=45)

    # Plot 2: Price distribution by platform
    sns.boxplot(data=df, x='platform', y='price', ax=axes[1])
    axes[1].set_title('Price Distribution by Platform')
    axes[1].set_xlabel('Platform')
    axes[1].set_ylabel('Price (¥)')
    axes[1].tick_params(axis='x', rotation=45)

    # Adjust layout and save
    plt.tight_layout()
    output_dir = Path("analysis")
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / "price_analysis.png")
    logger.info("Saved price analysis visualization")


def main():
    """Run the analysis."""
    logger.info("Starting data analysis")

    # Load data
    data = load_data()
    if not data:
        logger.error("No data found for analysis")
        return

    # Cluster jobs
    clustered_data = cluster_jobs(data)

    # Analyze prices
    analyze_prices(clustered_data)

    logger.info("Analysis complete")


if __name__ == "__main__":
    main() 