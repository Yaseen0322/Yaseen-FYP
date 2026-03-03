"""
ML Classifier Service - Phase 3
Machine learning-based domain and app classification
"""
from typing import Tuple, Optional, List, Dict
from sqlalchemy.orm import Session
from app.models.browser_usage import DomainRule
from app.models.integrations import MLClassification

# Pre-trained categories based on common patterns
DOMAIN_PATTERNS = {
    # Development & Work
    "productive": {
        "keywords": [
            "github", "gitlab", "bitbucket", "stackoverflow", "docs", 
            "documentation", "api", "dev", "developer", "cloud", 
            "aws", "azure", "gcp", "jira", "confluence", "notion",
            "figma", "sketch", "linear", "asana", "trello", "monday",
            "slack", "teams", "zoom", "meet", "calendar"
        ],
        "domains": [
            "github.com", "gitlab.com", "stackoverflow.com", "docs.google.com",
            "notion.so", "figma.com", "linear.app", "asana.com", "trello.com",
            "slack.com", "teams.microsoft.com", "zoom.us"
        ]
    },
    # Entertainment & Social
    "unproductive": {
        "keywords": [
            "facebook", "twitter", "instagram", "tiktok", "snapchat",
            "youtube", "netflix", "hulu", "disney", "twitch", "reddit",
            "game", "gaming", "play", "bet", "casino", "porn", "xxx"
        ],
        "domains": [
            "facebook.com", "twitter.com", "instagram.com", "tiktok.com",
            "youtube.com", "netflix.com", "reddit.com", "twitch.tv",
            "9gag.com", "buzzfeed.com"
        ]
    },
    # Learning & Education
    "productive": {
        "keywords": [
            "learn", "course", "tutorial", "education", "training",
            "academy", "university", "school", "study", "lecture"
        ],
        "domains": [
            "coursera.org", "udemy.com", "edx.org", "pluralsight.com",
            "linkedin.com/learning", "skillshare.com", "khan.academy"
        ]
    }
}

APP_PATTERNS = {
    "productive": {
        "keywords": [
            "code", "studio", "ide", "terminal", "git", "docker",
            "office", "word", "excel", "powerpoint", "outlook",
            "slack", "teams", "zoom", "figma", "sketch", "photoshop",
            "illustrator", "xcode", "android", "postman", "insomnia"
        ]
    },
    "unproductive": {
        "keywords": [
            "game", "steam", "epic", "spotify", "music", "video",
            "vlc", "netflix", "discord", "telegram"
        ]
    }
}


class MLClassifier:
    def __init__(self, db: Session):
        self.db = db
        self.cache = {}
    
    def classify_domain(
        self, 
        domain: str, 
        org_id: int,
        dept_id: Optional[int] = None
    ) -> Tuple[str, str, int]:
        """
        Classify a domain as productive/unproductive/neutral
        Returns: (category, label, confidence)
        """
        domain_lower = domain.lower()
        
        # Check cache first
        cache_key = f"domain:{domain_lower}:{org_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check existing rules in database
        rule = self.db.query(DomainRule).filter(
            DomainRule.org_id == org_id,
            DomainRule.domain == domain
        ).first()
        
        if rule:
            result = (rule.category, rule.label, 100)
            self.cache[cache_key] = result
            return result
        
        # Check ML classification history
        ml_result = self.db.query(MLClassification).filter(
            MLClassification.org_id == org_id,
            MLClassification.classification_type == "domain",
            MLClassification.input_value == domain,
            MLClassification.is_approved == True
        ).first()
        
        if ml_result:
            result = (ml_result.predicted_category, ml_result.predicted_label, ml_result.confidence)
            self.cache[cache_key] = result
            return result
        
        # Run ML classification
        category, label, confidence = self._ml_classify_domain(domain_lower)
        
        # Store result for future approval
        self._store_classification("domain", domain, category, label, confidence, org_id)
        
        result = (category, label, confidence)
        self.cache[cache_key] = result
        return result
    
    def _ml_classify_domain(self, domain: str) -> Tuple[str, str, int]:
        """
        ML-based domain classification using pattern matching
        In production, this could use a trained model
        """
        # Check direct domain matches
        for label, patterns in DOMAIN_PATTERNS.items():
            if label == "productive":
                if any(d in domain for d in patterns.get("domains", [])):
                    return ("Work", "productive", 95)
            elif label == "unproductive":
                if any(d in domain for d in patterns.get("domains", [])):
                    return ("Entertainment", "unproductive", 95)
        
        # Check keyword matches
        for label, patterns in DOMAIN_PATTERNS.items():
            keywords = patterns.get("keywords", [])
            matched_keywords = [k for k in keywords if k in domain]
            if matched_keywords:
                confidence = min(90, 50 + len(matched_keywords) * 10)
                category = "Work" if label == "productive" else "Entertainment"
                return (category, label, confidence)
        
        # Default to neutral
        return ("Other", "neutral", 50)
    
    def classify_app(
        self,
        app_name: str,
        org_id: int
    ) -> Tuple[str, str, int]:
        """
        Classify an application as productive/unproductive/neutral
        Returns: (category, label, confidence)
        """
        app_lower = app_name.lower()
        
        cache_key = f"app:{app_lower}:{org_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check ML classification history
        ml_result = self.db.query(MLClassification).filter(
            MLClassification.org_id == org_id,
            MLClassification.classification_type == "app",
            MLClassification.input_value == app_name,
            MLClassification.is_approved == True
        ).first()
        
        if ml_result:
            result = (ml_result.predicted_category, ml_result.predicted_label, ml_result.confidence)
            self.cache[cache_key] = result
            return result
        
        # Run ML classification
        category, label, confidence = self._ml_classify_app(app_lower)
        
        # Store result
        self._store_classification("app", app_name, category, label, confidence, org_id)
        
        result = (category, label, confidence)
        self.cache[cache_key] = result
        return result
    
    def _ml_classify_app(self, app_name: str) -> Tuple[str, str, int]:
        """ML-based app classification"""
        # Check productive keywords
        productive_keywords = APP_PATTERNS["productive"]["keywords"]
        if any(k in app_name for k in productive_keywords):
            return ("Development", "productive", 85)
        
        # Check unproductive keywords
        unproductive_keywords = APP_PATTERNS["unproductive"]["keywords"]
        if any(k in app_name for k in unproductive_keywords):
            return ("Entertainment", "unproductive", 85)
        
        # Default to neutral
        return ("Other", "neutral", 50)
    
    def _store_classification(
        self,
        classification_type: str,
        input_value: str,
        category: str,
        label: str,
        confidence: int,
        org_id: int
    ):
        """Store ML classification for approval"""
        existing = self.db.query(MLClassification).filter(
            MLClassification.org_id == org_id,
            MLClassification.classification_type == classification_type,
            MLClassification.input_value == input_value
        ).first()
        
        if not existing:
            classification = MLClassification(
                org_id=org_id,
                classification_type=classification_type,
                input_value=input_value,
                predicted_category=category,
                predicted_label=label,
                confidence=confidence,
                is_approved=False
            )
            self.db.add(classification)
            self.db.commit()
    
    def get_pending_classifications(self, org_id: int) -> List[MLClassification]:
        """Get classifications pending approval"""
        return self.db.query(MLClassification).filter(
            MLClassification.org_id == org_id,
            MLClassification.is_approved == False
        ).order_by(MLClassification.created_at.desc()).limit(100).all()
    
    def approve_classification(
        self,
        classification_id: int,
        user_id: int,
        approved_label: Optional[str] = None
    ):
        """Approve or correct a classification"""
        classification = self.db.query(MLClassification).filter(
            MLClassification.id == classification_id
        ).first()
        
        if classification:
            if approved_label:
                classification.predicted_label = approved_label
            classification.is_approved = True
            classification.approved_by = user_id
            self.db.commit()
            
            # Clear cache
            cache_key = f"{classification.classification_type}:{classification.input_value.lower()}:{classification.org_id}"
            if cache_key in self.cache:
                del self.cache[cache_key]


def get_classifier(db: Session) -> MLClassifier:
    """Get ML classifier instance"""
    return MLClassifier(db)
