"""
Job classification module for analyzing and categorizing freelance job listings.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger
import re
from typing import List, Dict, Tuple, Optional, Any
import jieba
import asyncio
import sys
import matplotlib as mpl

from src.config.config import Config
from tools.llm_api import query_llm, create_llm_client

def convert_to_serializable(obj: Any) -> Any:
    """Convert numpy types to Python native types for JSON serialization.
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object that can be JSON serialized
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

class JobClassifier:
    """Classifier for analyzing and categorizing freelance job listings."""
    
    def __init__(self, config: Config):
        """Initialize the job classifier.
        
        Args:
            config (Config): Configuration object
        """
        self.config = config
        self.logger = logger
        
        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-mpnet-base-v2')
        
        # Initialize clustering model
        self.kmeans = None
        self.scaler = StandardScaler()
        
        # Initialize LLM client
        self.llm_client = create_llm_client(provider="openai")
        
        # Set style for plots
        plt.style.use('seaborn-v0_8')
        
        # Configure Chinese font support
        self._setup_chinese_font()
        
    def _setup_chinese_font(self):
        """Setup Chinese font support for matplotlib."""
        # Try different Chinese fonts in order of preference
        chinese_fonts = [
            'Microsoft YaHei',  # Windows
            'SimHei',          # Windows
            'SimSun',          # Windows
            'NSimSun',         # Windows
            'PingFang SC',     # macOS
            'Hiragino Sans GB', # macOS
            'Heiti SC',        # macOS
            'WenQuanYi Micro Hei', # Linux
            'Droid Sans Fallback', # Linux
            'Noto Sans CJK SC',   # Linux
            'Source Han Sans CN'  # Linux
        ]
        
        # Find the first available font
        available_font = None
        for font in chinese_fonts:
            try:
                if any(f for f in mpl.font_manager.findSystemFonts() if font.lower() in f.lower()):
                    available_font = font
                    break
            except:
                continue
        
        if available_font:
            self.logger.info(f"Using Chinese font: {available_font}")
            plt.rcParams['font.family'] = [available_font]
        else:
            self.logger.warning("No suitable Chinese font found. Chinese characters may not display correctly.")
            
        # Set fallback font
        plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display
        
    def load_data(self) -> pd.DataFrame:
        """Load and combine data from all sources.
        
        Returns:
            pd.DataFrame: Combined dataset
        """
        all_data = []
        working_files = 0
        
        # Load data from each source
        for source in ['yuanjisong', 'sxsapi']:
            try:
                file_path = Path(self.config.output_dir) / f"{source}.json"
                self.logger.info(f"Loading data from {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Add source field
                    for item in data:
                        item['source'] = source
                    all_data.extend(data)
                    working_files += 1
                    self.logger.info(f"Successfully loaded {len(data)} records from {source}")
            except Exception as e:
                self.logger.error(f"Error loading data from {source}: {str(e)}")
                
        if working_files == 0:
            raise ValueError("No data files could be loaded successfully")
                
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        self.logger.info(f"Loaded {len(df)} job listings in total")
        
        return df
        
    def preprocess_text(self, text: str) -> str:
        """Preprocess text data.
        
        Args:
            text (str): Raw text
            
        Returns:
            str: Preprocessed text
        """
        if not isinstance(text, str):
            return ""
            
        # Remove special characters and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Tokenize Chinese text
        words = jieba.cut(text)
        text = ' '.join(words)
        
        return text.strip()
        
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """Prepare features for clustering using sentence transformers.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            
        Returns:
            Tuple[np.ndarray, List[str]]: Feature matrix and feature names
        """
        # Combine title and description
        df['text'] = df['title'].fillna('') + ' ' + df['description'].fillna('')
        
        # Preprocess text
        df['processed_text'] = df['text'].apply(self.preprocess_text)
        
        # Generate embeddings using sentence transformers
        self.logger.info("Generating embeddings using sentence transformers...")
        embeddings = self.model.encode(df['processed_text'].tolist(), show_progress_bar=True)
        
        # Scale features
        features = self.scaler.fit_transform(embeddings)
        
        # Generate feature names (dimensions)
        feature_names = [f"dim_{i}" for i in range(embeddings.shape[1])]
        
        return features, feature_names
        
    def find_optimal_clusters(self, features: np.ndarray, max_clusters: int = 10) -> int:
        """Find optimal number of clusters using silhouette score.
        
        Args:
            features (np.ndarray): Feature matrix
            max_clusters (int): Maximum number of clusters to try
            
        Returns:
            int: Optimal number of clusters
        """
        scores = []
        n_clusters_range = range(2, max_clusters + 1)
        
        for n_clusters in n_clusters_range:
            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=42,
                n_init=10
            )
            cluster_labels = kmeans.fit_predict(features)
            silhouette_avg = silhouette_score(features, cluster_labels)
            scores.append(silhouette_avg)
            self.logger.info(f"Silhouette score for {n_clusters} clusters: {silhouette_avg:.3f}")
            
        # Plot silhouette scores
        plt.figure(figsize=(10, 6))
        plt.plot(n_clusters_range, scores, 'bo-')
        plt.xlabel('聚类数量')
        plt.ylabel('轮廓系数')
        plt.title('轮廓系数与聚类数量关系图')
        plt.grid(True)
        plt.savefig(Path(self.config.output_dir) / 'silhouette_scores.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Return optimal number of clusters
        optimal_clusters = n_clusters_range[np.argmax(scores)]
        self.logger.info(f"Optimal number of clusters: {optimal_clusters}")
        return optimal_clusters
        
    async def generate_cluster_labels(self, df: pd.DataFrame, cluster_ids: np.ndarray) -> List[str]:
        """Generate descriptive labels for clusters using LLM.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            cluster_ids (np.ndarray): Cluster assignments
            
        Returns:
            List[str]: Cluster labels
        """
        labels = []
        
        for cluster_id in range(len(np.unique(cluster_ids))):
            # Get sample of jobs from cluster
            cluster_df = df[cluster_ids == cluster_id]
            sample_size = min(5, len(cluster_df))
            sample_jobs = cluster_df.sample(n=sample_size)
            
            # Create prompt
            prompt = "Based on the following job listings, provide a concise category label (1-3 words) that best describes this type of work. The label should be in Chinese:\n\n"
            for _, job in sample_jobs.iterrows():
                prompt += f"Title: {job['title']}\n"
                prompt += f"Description: {job['description'][:200]}...\n\n"
            
            try:
                # Get label from LLM using the local implementation
                response = query_llm(
                    prompt=prompt,
                    client=self.llm_client,
                    provider="openai"
                )
                
                if response and not response.startswith('Error:'):
                    labels.append(response.strip())
                    self.logger.info(f"Generated label for cluster {cluster_id}: {response.strip()}")
                else:
                    self.logger.error(f"Failed to get response for cluster {cluster_id}: {response}")
                    labels.append(f"类别 {cluster_id + 1}")
            except Exception as e:
                self.logger.error(f"Error generating label for cluster {cluster_id}: {str(e)}")
                labels.append(f"类别 {cluster_id + 1}")
                
        return labels
        
    def plot_price_distributions(self, df: pd.DataFrame, cluster_ids: np.ndarray, cluster_labels: List[str]):
        """Plot price distributions by cluster.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            cluster_ids (np.ndarray): Cluster assignments
            cluster_labels (List[str]): Cluster labels
        """
        plt.figure(figsize=(15, 8))
        
        # Create violin plot
        df['cluster'] = cluster_ids
        df['cluster_label'] = df['cluster'].map(dict(enumerate(cluster_labels)))
        
        # Handle different price fields from different sources
        df['price'] = df.apply(
            lambda x: x.get('total_price', x.get('price', 0)),
            axis=1
        )
        
        # Remove outliers for better visualization
        df['price'] = df['price'].clip(upper=df['price'].quantile(0.95))
        
        # Create plot
        sns.violinplot(data=df, x='cluster_label', y='price')
        plt.xticks(rotation=45, ha='right')
        plt.xlabel('工作类别')
        plt.ylabel('价格 (¥)')
        plt.title('各类别工作价格分布')
        
        # Save plot with high DPI and tight layout
        plt.tight_layout()
        plt.savefig(Path(self.config.output_dir) / 'price_distributions.png', dpi=300, bbox_inches='tight')
        plt.close()
        
    def generate_cluster_summary(self, df: pd.DataFrame, cluster_ids: np.ndarray, cluster_labels: List[str]) -> Dict:
        """Generate summary statistics for each cluster.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            cluster_ids (np.ndarray): Cluster assignments
            cluster_labels (List[str]): Cluster labels
            
        Returns:
            Dict: Summary statistics
        """
        summary = {}
        
        df['cluster'] = cluster_ids
        df['cluster_label'] = df['cluster'].map(dict(enumerate(cluster_labels)))
        
        for cluster_id, label in enumerate(cluster_labels):
            cluster_df = df[df['cluster'] == cluster_id]
            
            # Calculate statistics
            stats = {
                'size': int(len(cluster_df)),  # Convert numpy.int64 to int
                'avg_price': float(cluster_df['price'].mean()),  # Convert numpy.float64 to float
                'median_price': float(cluster_df['price'].median()),
                'min_price': float(cluster_df['price'].min()),
                'max_price': float(cluster_df['price'].max()),
                'sample_titles': cluster_df['title'].sample(min(5, len(cluster_df))).tolist()
            }
            
            summary[label] = stats
            
        return summary
        
    async def analyze(self) -> Dict:
        """Perform complete analysis of job listings.
        
        Returns:
            Dict: Analysis results
        """
        # Load and preprocess data
        df = self.load_data()
        features, feature_names = self.prepare_features(df)
        
        # Find optimal number of clusters
        n_clusters = self.find_optimal_clusters(features)
        
        # Perform clustering
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_ids = self.kmeans.fit_predict(features)
        
        # Generate cluster labels
        cluster_labels = await self.generate_cluster_labels(df, cluster_ids)
        
        # Create visualizations
        self.plot_price_distributions(df, cluster_ids, cluster_labels)
        
        # Generate summary
        summary = self.generate_cluster_summary(df, cluster_ids, cluster_labels)
        
        # Convert numpy types to Python native types for JSON serialization
        feature_importance = {
            name: convert_to_serializable(value)
            for name, value in zip(feature_names, self.kmeans.cluster_centers_.mean(axis=0))
        }
        
        # Save results
        results = {
            'cluster_labels': cluster_labels,
            'summary': summary,
            'feature_importance': feature_importance
        }
        
        with open(Path(self.config.output_dir) / 'analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        return results 