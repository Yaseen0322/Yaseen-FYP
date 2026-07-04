"""
ML Classifier Service - Phase 3
Machine learning-based domain and app classification
"""
from typing import Tuple, Optional, List, Dict
from sqlalchemy.orm import Session
from app.models.browser_usage import DomainRule
from app.models.integrations import MLClassification


def normalize_domain(domain: str) -> str:
    normalized = (domain or "").strip().lower().rstrip(".")
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized


DOMAIN_PATTERNS = [
    {
        "label": "productive",
        "category": "Development/Work",
        "keywords": [
            "github", "gitlab", "bitbucket", "stackoverflow", "docs",
            "documentation", "api", "dev", "developer", "cloud",
            "aws", "azure", "gcp", "jira", "confluence", "notion",
            "figma", "sketch", "linear", "asana", "trello", "monday",
            "slack", "teams", "zoom", "meet", "calendar",
        ],
        "domains": [
            "github.com", "gitlab.com", "stackoverflow.com", "docs.google.com",
            "notion.so", "figma.com", "linear.app", "asana.com", "trello.com",
            "slack.com", "teams.microsoft.com", "zoom.us",
        ],
    },
    {
        "label": "productive",
        "category": "Learning",
        "keywords": [
            "learn", "course", "tutorial", "education", "training",
            "academy", "university", "school", "study", "lecture",
        ],
        "domains": [
            "coursera.org", "udemy.com", "edx.org", "pluralsight.com",
            "linkedin.com/learning", "skillshare.com", "khan.academy",
        ],
    },
    {
        "label": "unproductive",
        "category": "Social/Entertainment",
        "keywords": [
            "facebook", "twitter", "instagram", "tiktok", "snapchat",
            "youtube", "netflix", "hulu", "disney", "twitch", "reddit",
            "game", "gaming", "play", "bet", "casino", "porn", "xxx",
        ],
        "domains": [
            "facebook.com", "twitter.com", "instagram.com", "tiktok.com",
            "youtube.com", "netflix.com", "reddit.com", "twitch.tv",
            "9gag.com", "buzzfeed.com",
        ],
    },
]

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


def classify_domain_by_patterns(domain: str) -> Tuple[str, str, int]:
    """
    Pure pattern-based domain classification for read-only reporting paths.
    """
    normalized_domain = normalize_domain(domain)

    for pattern in DOMAIN_PATTERNS:
        if any(candidate in normalized_domain for candidate in pattern.get("domains", [])):
            return (pattern["category"], pattern["label"], 95)

    for pattern in DOMAIN_PATTERNS:
        keywords = pattern.get("keywords", [])
        matched_keywords = [keyword for keyword in keywords if keyword in normalized_domain]
        if matched_keywords:
            confidence = min(90, 50 + len(matched_keywords) * 10)
            return (pattern["category"], pattern["label"], confidence)

    return ("Other", "neutral", 50)


def classify_app_by_patterns(app_name: str) -> Tuple[str, str, int]:
    """
    Pure pattern-based app classification for summary calculations.
    """
    app_lower = app_name.strip().lower()

    productive_keywords = APP_PATTERNS["productive"]["keywords"]
    if any(keyword in app_lower for keyword in productive_keywords):
        return ("Development", "productive", 85)

    unproductive_keywords = APP_PATTERNS["unproductive"]["keywords"]
    if any(keyword in app_lower for keyword in unproductive_keywords):
        return ("Entertainment", "unproductive", 85)

    return ("Other", "neutral", 50)


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
        normalized_domain = normalize_domain(domain)
        
        # Check cache first
        cache_key = f"domain:{normalized_domain}:{org_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check existing rules in database
        rule = self.db.query(DomainRule).filter(
            DomainRule.org_id == org_id,
            DomainRule.domain == normalized_domain
        ).first()
        
        if rule:
            result = (rule.category, rule.label, 100)
            self.cache[cache_key] = result
            return result
        
        # Check ML classification history
        ml_result = self.db.query(MLClassification).filter(
            MLClassification.org_id == org_id,
            MLClassification.classification_type == "domain",
            MLClassification.input_value == normalized_domain,
            MLClassification.is_approved == True
        ).first()
        
        if ml_result:
            result = (ml_result.predicted_category, ml_result.predicted_label, ml_result.confidence)
            self.cache[cache_key] = result
            return result
        
        # Run ML classification
        category, label, confidence = self._ml_classify_domain(normalized_domain)
        
        # Store result for future approval
        self._store_classification("domain", normalized_domain, category, label, confidence, org_id)
        
        result = (category, label, confidence)
        self.cache[cache_key] = result
        return result
    
    def _ml_classify_domain(self, domain: str) -> Tuple[str, str, int]:
        """
        ML-based domain classification using pattern matching
        In production, this could use a trained model
        """
        return classify_domain_by_patterns(domain)
    
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
        return classify_app_by_patterns(app_name)
    
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
        normalized_input = input_value.strip().lower()
        existing = self.db.query(MLClassification).filter(
            MLClassification.org_id == org_id,
            MLClassification.classification_type == classification_type,
            MLClassification.input_value == normalized_input
        ).first()
        
        if not existing:
            classification = MLClassification(
                org_id=org_id,
                classification_type=classification_type,
                input_value=normalized_input,
                predicted_category=category,
                predicted_label=label,
                confidence=confidence,
                is_approved=False
            )
            self.db.add(classification)
    
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
