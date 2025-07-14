from pathlib import Path
import spacy
import re
from typing import Dict, List
from spacy.matcher import Matcher

class SpacyNERPIIDetector:
    def __init__(self, model_path: str):
        self.model_path = model_path
        
        self.nlp = spacy.load(Path(model_path))
        self.matcher = Matcher(self.nlp.vocab)
        self._setup_custom_patterns()
        
        self.pii_entity_mapping = {
            'PERSON': 'person_name',
            'ORG': 'organization',
            'GPE': 'location',
            'LOC': 'location',
            'DATE': 'date',
            'TIME': 'time',
            'MONEY': 'financial',
            'CARDINAL': 'number',
            'ORDINAL': 'number'
        }
        
        self.custom_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        }
    
    def _setup_custom_patterns(self):
        email_pattern = [
            {"LIKE_EMAIL": True}
        ]
        self.matcher.add("EMAIL", [email_pattern])
        
        phone_pattern = [
            {"SHAPE": "ddd-ddd-dddd"},
            {"SHAPE": "(ddd) ddd-dddd"},
            {"TEXT": {"REGEX": r"\(\d{3}\)\s?\d{3}-\d{4}"}}
        ]
        self.matcher.add("PHONE", [phone_pattern])
        
        url_pattern = [
            {"LIKE_URL": True}
        ]
        self.matcher.add("URL", [url_pattern])
    
    def detect_pii_ner(self, text: str) -> List[Dict]:
        doc = self.nlp(text)
        pii_entities = []
        
        for ent in doc.ents:
            if ent.label_ in self.pii_entity_mapping:
                pii_entities.append({
                    'entity_type': self.pii_entity_mapping[ent.label_],
                    'spacy_label': ent.label_,
                    'text': ent.text,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 1.0
                })
        
        return pii_entities
    
    def detect_pii_matcher(self, text: str) -> List[Dict]:
        doc = self.nlp(text)
        matches = self.matcher(doc)
        pii_entities = []
        
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]
            pii_entities.append({
                'entity_type': label.lower(),
                'spacy_label': label,
                'text': span.text,
                'start': span.start_char,
                'end': span.end_char,
                'confidence': 1.0
            })
        
        return pii_entities
    
    def detect_pii_regex(self, text: str) -> List[Dict]:
        pii_entities = []
        
        for pii_type, pattern in self.custom_patterns.items():
            for match in re.finditer(pattern, text):
                pii_entities.append({
                    'entity_type': pii_type,
                    'spacy_label': pii_type.upper(),
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 1.0
                })
        
        return pii_entities
    
    def detect_pii_combined(self, text: str) -> List[Dict]:
        all_entities = []
        
        all_entities.extend(self.detect_pii_ner(text))
        
        all_entities.extend(self.detect_pii_matcher(text))
        
        all_entities.extend(self.detect_pii_regex(text))
        
        unique_entities = []
        seen = set()
        
        for entity in all_entities:
            key = (entity['text'], entity['start'], entity['end'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return sorted(unique_entities, key=lambda x: x['start'])
    
