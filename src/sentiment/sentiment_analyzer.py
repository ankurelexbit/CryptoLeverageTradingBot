import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import tweepy
import praw
from newspaper import Article
import aiohttp
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from loguru import logger
from dataclasses import dataclass
import re
from collections import defaultdict
import pandas as pd
from src.config import settings


@dataclass
class SentimentData:
    source: str
    symbol: str
    sentiment_score: float  # -1 to 1
    volume: int  # Number of mentions
    key_topics: List[str]
    timestamp: datetime
    raw_data: Optional[Dict] = None


class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self._setup_apis()
        self.crypto_keywords = self._load_crypto_keywords()
        
    def _setup_apis(self):
        """Initialize API clients for social media platforms"""
        # Twitter API
        if settings.twitter_api_key:
            auth = tweepy.OAuthHandler(settings.twitter_api_key, settings.twitter_api_secret)
            auth.set_access_token(settings.twitter_access_token, settings.twitter_access_token_secret)
            self.twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
        else:
            self.twitter_api = None
            
        # Reddit API
        if settings.reddit_client_id:
            self.reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent
            )
        else:
            self.reddit = None
            
    def _load_crypto_keywords(self) -> Dict[str, List[str]]:
        """Load cryptocurrency-specific keywords and aliases"""
        return {
            'BTCUSDT': ['bitcoin', 'btc', 'bitcoin futures', '#bitcoin', '#btc'],
            'ETHUSDT': ['ethereum', 'eth', 'ethereum futures', '#ethereum', '#eth'],
            'BNBUSDT': ['binance coin', 'bnb', '#bnb', 'binance'],
            'SOLUSDT': ['solana', 'sol', '#solana', '#sol'],
            'XRPUSDT': ['ripple', 'xrp', '#xrp', '#ripple'],
            'ADAUSDT': ['cardano', 'ada', '#cardano', '#ada'],
            'AVAXUSDT': ['avalanche', 'avax', '#avalanche', '#avax'],
            'DOTUSDT': ['polkadot', 'dot', '#polkadot', '#dot'],
            'MATICUSDT': ['polygon', 'matic', '#polygon', '#matic'],
            'LINKUSDT': ['chainlink', 'link', '#chainlink', '#link'],
        }
        
    async def analyze_sentiment(self, symbol: str) -> Dict[str, SentimentData]:
        """Analyze sentiment from multiple sources"""
        tasks = []
        
        if self.twitter_api:
            tasks.append(self._analyze_twitter(symbol))
            
        if self.reddit:
            tasks.append(self._analyze_reddit(symbol))
            
        tasks.append(self._analyze_news(symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        sentiment_data = {}
        for result in results:
            if isinstance(result, SentimentData):
                sentiment_data[result.source] = result
            elif isinstance(result, Exception):
                logger.error(f"Error in sentiment analysis: {result}")
                
        # Aggregate sentiment
        if sentiment_data:
            sentiment_data['aggregate'] = self._aggregate_sentiment(list(sentiment_data.values()))
            
        return sentiment_data
        
    async def _analyze_twitter(self, symbol: str) -> SentimentData:
        """Analyze Twitter sentiment"""
        try:
            keywords = self.crypto_keywords.get(symbol, [symbol.replace('USDT', '')])
            query = ' OR '.join(keywords) + ' -filter:retweets'
            
            tweets = []
            sentiments = []
            topics = defaultdict(int)
            
            # Search recent tweets
            for tweet in tweepy.Cursor(
                self.twitter_api.search_tweets,
                q=query,
                lang='en',
                tweet_mode='extended',
                result_type='mixed'
            ).items(100):
                
                text = tweet.full_text
                tweets.append(text)
                
                # Analyze sentiment
                sentiment = self._calculate_sentiment(text)
                sentiments.append(sentiment)
                
                # Extract topics
                self._extract_topics(text, topics)
                
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                volume = len(tweets)
                key_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
                
                return SentimentData(
                    source='twitter',
                    symbol=symbol,
                    sentiment_score=avg_sentiment,
                    volume=volume,
                    key_topics=[topic[0] for topic in key_topics],
                    timestamp=datetime.now(),
                    raw_data={'sample_tweets': tweets[:5]}
                )
            else:
                return SentimentData(
                    source='twitter',
                    symbol=symbol,
                    sentiment_score=0.0,
                    volume=0,
                    key_topics=[],
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Twitter sentiment for {symbol}: {e}")
            raise e
            
    async def _analyze_reddit(self, symbol: str) -> SentimentData:
        """Analyze Reddit sentiment"""
        try:
            keywords = self.crypto_keywords.get(symbol, [symbol.replace('USDT', '')])
            
            posts = []
            sentiments = []
            topics = defaultdict(int)
            
            # Search multiple subreddits
            for subreddit_name in ['cryptocurrency', 'bitcoin', 'ethtrader', 'binance']:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search posts
                for post in subreddit.search(' OR '.join(keywords), time_filter='day', limit=25):
                    text = f"{post.title} {post.selftext}"
                    posts.append(text)
                    
                    # Analyze sentiment
                    sentiment = self._calculate_sentiment(text)
                    sentiments.append(sentiment)
                    
                    # Extract topics
                    self._extract_topics(text, topics)
                    
                    # Analyze top comments
                    post.comments.replace_more(limit=0)
                    for comment in post.comments[:5]:
                        if hasattr(comment, 'body'):
                            comment_sentiment = self._calculate_sentiment(comment.body)
                            sentiments.append(comment_sentiment)
                            
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                volume = len(posts)
                key_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
                
                return SentimentData(
                    source='reddit',
                    symbol=symbol,
                    sentiment_score=avg_sentiment,
                    volume=volume,
                    key_topics=[topic[0] for topic in key_topics],
                    timestamp=datetime.now(),
                    raw_data={'sample_posts': posts[:5]}
                )
            else:
                return SentimentData(
                    source='reddit',
                    symbol=symbol,
                    sentiment_score=0.0,
                    volume=0,
                    key_topics=[],
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Reddit sentiment for {symbol}: {e}")
            raise e
            
    async def _analyze_news(self, symbol: str) -> SentimentData:
        """Analyze news sentiment"""
        try:
            keywords = self.crypto_keywords.get(symbol, [symbol.replace('USDT', '')])
            news_sites = ['coindesk.com', 'cointelegraph.com', 'decrypt.co', 'theblock.co']
            
            articles = []
            sentiments = []
            topics = defaultdict(int)
            
            async with aiohttp.ClientSession() as session:
                for keyword in keywords[:2]:  # Limit queries
                    for site in news_sites:
                        url = f"https://www.google.com/search?q={keyword}+site:{site}&tbs=qdr:d"
                        
                        try:
                            # Note: In production, use a proper news API like NewsAPI
                            # This is a simplified example
                            async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                                if response.status == 200:
                                    # Parse and extract article URLs
                                    # In production, implement proper parsing
                                    pass
                        except Exception as e:
                            logger.error(f"Error fetching news from {site}: {e}")
                            
            # For now, return mock data - in production, implement proper news scraping
            return SentimentData(
                source='news',
                symbol=symbol,
                sentiment_score=0.1,  # Placeholder
                volume=10,
                key_topics=['futures', 'trading', 'market', 'analysis', 'price'],
                timestamp=datetime.now(),
                raw_data={'articles_analyzed': 10}
            )
            
        except Exception as e:
            logger.error(f"Error analyzing news sentiment for {symbol}: {e}")
            raise e
            
    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score using multiple methods"""
        # Clean text
        text = re.sub(r'http\S+', '', text)  # Remove URLs
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove special characters
        
        # VADER sentiment
        vader_scores = self.vader.polarity_scores(text)
        vader_compound = vader_scores['compound']
        
        # TextBlob sentiment
        try:
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
        except:
            textblob_polarity = 0
            
        # Combine scores (weighted average)
        combined_score = (vader_compound * 0.7) + (textblob_polarity * 0.3)
        
        return max(min(combined_score, 1.0), -1.0)
        
    def _extract_topics(self, text: str, topics: Dict[str, int]):
        """Extract key topics from text"""
        # Common crypto trading terms
        trading_terms = [
            'bullish', 'bearish', 'moon', 'pump', 'dump', 'hodl', 'fomo',
            'support', 'resistance', 'breakout', 'reversal', 'trend',
            'long', 'short', 'leverage', 'liquidation', 'futures'
        ]
        
        text_lower = text.lower()
        for term in trading_terms:
            if term in text_lower:
                topics[term] += text_lower.count(term)
                
    def _aggregate_sentiment(self, sentiments: List[SentimentData]) -> SentimentData:
        """Aggregate sentiment from multiple sources"""
        if not sentiments:
            return SentimentData(
                source='aggregate',
                symbol='',
                sentiment_score=0.0,
                volume=0,
                key_topics=[],
                timestamp=datetime.now()
            )
            
        # Weight different sources
        weights = {
            'twitter': 0.4,
            'reddit': 0.3,
            'news': 0.3
        }
        
        total_weight = 0
        weighted_sentiment = 0
        total_volume = 0
        all_topics = defaultdict(int)
        
        for sentiment in sentiments:
            weight = weights.get(sentiment.source, 0.2)
            weighted_sentiment += sentiment.sentiment_score * weight * sentiment.volume
            total_weight += weight * sentiment.volume
            total_volume += sentiment.volume
            
            for topic in sentiment.key_topics:
                all_topics[topic] += 1
                
        avg_sentiment = weighted_sentiment / total_weight if total_weight > 0 else 0
        top_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return SentimentData(
            source='aggregate',
            symbol=sentiments[0].symbol if sentiments else '',
            sentiment_score=avg_sentiment,
            volume=total_volume,
            key_topics=[topic[0] for topic in top_topics],
            timestamp=datetime.now()
        )