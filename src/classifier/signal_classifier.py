from typing import Dict, List, Any, Tuple
import re
import logging
from datetime import datetime, timedelta

from config.settings import SIGNAL_WEIGHTS

logger = logging.getLogger(__name__)

class SignalClassifier:
    """Classify feed items into signal categories: red, yellow, green"""
    
    def __init__(self):
        self.high_impact_keywords = [kw.lower() for kw in SIGNAL_WEIGHTS["high_impact_keywords"]]
        self.curious_keywords = [kw.lower() for kw in SIGNAL_WEIGHTS["curious_keywords"]]
        self.insight_keywords = [kw.lower() for kw in SIGNAL_WEIGHTS["insight_keywords"]]
        
        # Score thresholds for different sources
        self.score_thresholds = {
            "github": {"red": 100, "yellow": 20},  # stars
            "reddit": {"red": 50, "yellow": 10},   # upvotes  
            "hackernews": {"red": 100, "yellow": 20}, # points
            "arxiv": {"red": 0, "yellow": 0}       # no scores
        }
        
    def classify(self, item: Dict[str, Any]) -> Tuple[str, float]:
        """
        Classify an item's signal type
        
        Args:
            item: Item dictionary with title, description, source, etc.
            
        Returns:
            Tuple of (signal_type, confidence_score)
            signal_type: "red", "yellow", or "green"  
            confidence_score: 0.0 to 1.0
        """
        try:
            # Combine title and description for analysis
            text = self._get_analysis_text(item)
            source = item.get("source", "")
            score = item.get("score", 0)
            
            # Calculate different signal scores
            high_impact_score = self._calculate_keyword_score(text, self.high_impact_keywords)
            curious_score = self._calculate_keyword_score(text, self.curious_keywords)
            insight_score = self._calculate_keyword_score(text, self.insight_keywords)
            
            # Source-specific scoring
            source_score = self._calculate_source_score(item)
            
            # Authority scoring (author, domain, etc.)
            authority_score = self._calculate_authority_score(item)
            
            # Recency bonus
            recency_score = self._calculate_recency_score(item)
            
            # Combine all scores with weights
            red_score = (
                high_impact_score * 0.4 +
                source_score * 0.3 + 
                authority_score * 0.2 +
                recency_score * 0.1
            )
            
            yellow_score = (
                curious_score * 0.4 +
                source_score * 0.2 +
                authority_score * 0.2 +
                recency_score * 0.2
            )
            
            green_score = (
                insight_score * 0.5 +
                authority_score * 0.3 +
                recency_score * 0.2
            )
            
            # Determine classification
            max_score = max(red_score, yellow_score, green_score)
            
            if red_score == max_score and red_score > 0.3:
                signal_type = "red"
                confidence = min(red_score, 1.0)
            elif yellow_score == max_score and yellow_score > 0.2:
                signal_type = "yellow" 
                confidence = min(yellow_score, 1.0)
            else:
                signal_type = "green"
                confidence = min(max(green_score, 0.1), 1.0)
            
            logger.debug(f"Classified '{item.get('title', '')[:30]}...' as {signal_type} (confidence: {confidence:.2f})")
            
            return signal_type, confidence
            
        except Exception as e:
            logger.error(f"Error classifying item: {e}")
            return "green", 0.1  # Default fallback
    
    def _get_analysis_text(self, item: Dict[str, Any]) -> str:
        """Combine title and description for analysis"""
        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        
        # Limit description length to avoid overwhelming title
        if len(description) > 200:
            description = description[:200]
            
        return f"{title} {description}".strip()
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword match score"""
        if not text or not keywords:
            return 0.0
            
        matches = 0
        total_keywords = len(keywords)
        
        for keyword in keywords:
            # Use word boundaries for better matching
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                matches += 1
        
        # Normalize by number of keywords and add bonus for multiple matches
        base_score = matches / total_keywords
        bonus = min(matches * 0.1, 0.3)  # Max 30% bonus
        
        return min(base_score + bonus, 1.0)
    
    def _calculate_source_score(self, item: Dict[str, Any]) -> float:
        """Calculate score based on source-specific metrics"""
        source = item.get("source", "")
        score = item.get("score", 0)
        
        if source not in self.score_thresholds:
            return 0.1
            
        thresholds = self.score_thresholds[source]
        
        if score >= thresholds["red"]:
            return 1.0
        elif score >= thresholds["yellow"]:
            return 0.6
        else:
            # Gradual scoring below yellow threshold
            return min(score / thresholds["yellow"] * 0.4, 0.4)
    
    def _calculate_authority_score(self, item: Dict[str, Any]) -> float:
        """Calculate authority score based on author, domain, etc."""
        score = 0.0
        
        # Check author reputation (basic heuristics)
        author = item.get("author", "").lower()
        if author:
            # Well-known AI researchers (very basic list)
            known_authors = [
                "yann lecun", "geoffrey hinton", "yoshua bengio", "andrew ng",
                "fei-fei li", "demis hassabis", "ilya sutskever", "andrej karpathy"
            ]
            
            if any(name in author for name in known_authors):
                score += 0.3
        
        # Check domain authority for URLs
        url = item.get("url", "").lower()
        authoritative_domains = [
            "arxiv.org", "github.com", "openai.com", "deepmind.com", 
            "research.google", "ai.facebook.com", "microsoft.com/research"
        ]
        
        if any(domain in url for domain in authoritative_domains):
            score += 0.2
            
        # Source-specific authority
        source = item.get("source", "")
        if source == "arxiv":
            score += 0.2  # Academic papers have inherent authority
        
        return min(score, 1.0)
    
    def _calculate_recency_score(self, item: Dict[str, Any]) -> float:
        """Calculate recency score - newer items get higher scores"""
        published_date = item.get("published_date")
        
        if not published_date:
            return 0.3  # Default for items without date
            
        try:
            if isinstance(published_date, str):
                # Try to parse string date
                published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            
            now = datetime.utcnow()
            age_hours = (now - published_date).total_seconds() / 3600
            
            # Scoring: 1.0 for <6 hours, linear decay to 0.1 over 7 days
            if age_hours < 6:
                return 1.0
            elif age_hours < 24:
                return 0.8
            elif age_hours < 72:  # 3 days
                return 0.6
            elif age_hours < 168:  # 7 days
                return 0.4
            else:
                return 0.1
                
        except Exception as e:
            logger.debug(f"Error calculating recency score: {e}")
            return 0.3
    
    def get_classification_summary(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics of classifications"""
        if not items:
            return {"total": 0, "red": 0, "yellow": 0, "green": 0}
        
        classifications = [self.classify(item)[0] for item in items]
        
        return {
            "total": len(items),
            "red": classifications.count("red"),
            "yellow": classifications.count("yellow"), 
            "green": classifications.count("green"),
            "red_pct": round(classifications.count("red") / len(items) * 100, 1),
            "yellow_pct": round(classifications.count("yellow") / len(items) * 100, 1),
            "green_pct": round(classifications.count("green") / len(items) * 100, 1)
        }