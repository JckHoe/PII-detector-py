import spacy
import re
import hashlib
import os
from typing import Dict, List, Tuple
from spacy.matcher import Matcher

class SpacyNERPIIDetector:
    def __init__(self, model_name: str = "en_core_web_sm"):
        try:
            # Check for bundled model path first
            spacy_model_path = os.environ.get('SPACY_MODEL_PATH')
            if spacy_model_path and os.path.exists(spacy_model_path):
                self.nlp = spacy.load(spacy_model_path)
            else:
                self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Model {model_name} not found. Please install with: python -m spacy download {model_name}")
            raise
        
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
    
    def anonymize_text(self, text: str, strategy: str = 'replace') -> Tuple[str, Dict]:
        entities = self.detect_pii_combined(text)
        anonymized_text = text
        mapping = {}
        
        entities_sorted = sorted(entities, key=lambda x: x['start'], reverse=True)
        
        for entity in entities_sorted:
            original = entity['text']
            start = entity['start']
            end = entity['end']
            entity_type = entity['entity_type']
            
            if strategy == 'hash':
                anonymized = f"[{entity_type.upper()}_{hashlib.md5(original.encode()).hexdigest()[:8]}]"
            elif strategy == 'placeholder':
                anonymized = f"[{entity_type.upper()}_REDACTED]"
            elif strategy == 'mask':
                if len(original) > 4:
                    anonymized = original[:2] + '*' * (len(original) - 4) + original[-2:]
                else:
                    anonymized = '*' * len(original)
            elif strategy == 'partial':
                if entity_type == 'email':
                    parts = original.split('@')
                    if len(parts) == 2:
                        anonymized = f"{parts[0][:2]}***@{parts[1]}"
                    else:
                        anonymized = f"[{entity_type.upper()}_REDACTED]"
                elif entity_type == 'phone':
                    anonymized = f"***-***-{original[-4:]}"
                elif entity_type == 'person_name':
                    words = original.split()
                    if len(words) > 1:
                        anonymized = f"{words[0][0]}*** {words[-1][0]}***"
                    else:
                        anonymized = f"{original[0]}***"
                else:
                    anonymized = f"[{entity_type.upper()}_REDACTED]"
            else:  # replace
                anonymized = f"[{entity_type.upper()}_REDACTED]"
            
            anonymized_text = anonymized_text[:start] + anonymized + anonymized_text[end:]
            mapping[anonymized] = original
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_anonymize_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return anonymized_text, mapping

def demo_spacy_detection():
    try:
        detector = SpacyNERPIIDetector()
        
        sample_text = """
        Hi Dr. Sarah Johnson, my email is sarah.johnson@hospital.com and my phone is (555) 123-4567.
        I work at Mayo Clinic in Rochester, Minnesota. I was born on March 15, 1985.
        My address is 123 Main Street, New York, NY 10001.
        Please visit our website at https://hospital.com for more information.
        My patient ID is P123456 and the appointment is scheduled for tomorrow at 2:30 PM.
        The consultation fee is $150.
        """
        
        print("Original text:")
        print(sample_text)
        print("\n" + "="*60)
        
        print("NER Detection:")
        ner_entities = detector.detect_pii_ner(sample_text)
        for entity in ner_entities:
            print(f"- {entity['entity_type']} ({entity['spacy_label']}): '{entity['text']}'")
        
        print("\nMatcher Detection:")
        matcher_entities = detector.detect_pii_matcher(sample_text)
        for entity in matcher_entities:
            print(f"- {entity['entity_type']}: '{entity['text']}'")
        
        print("\nRegex Detection:")
        regex_entities = detector.detect_pii_regex(sample_text)
        for entity in regex_entities:
            print(f"- {entity['entity_type']}: '{entity['text']}'")
        
        print("\nCombined Detection:")
        combined_entities = detector.detect_pii_combined(sample_text)
        for entity in combined_entities:
            print(f"- {entity['entity_type']}: '{entity['text']}'")
        
        print("\n" + "="*60)
        
        strategies = ['replace', 'hash', 'mask', 'partial']
        for strategy in strategies:
            anonymized, mapping = detector.anonymize_text(sample_text, strategy)
            print(f"\nAnonymized text ({strategy} strategy):")
            print(anonymized)
            
    except Exception as e:
        print(f"Error: {e}")
        print("Please install spaCy and download the English model:")
        print("pip install spacy")
        print("python -m spacy download en_core_web_sm")

if __name__ == "__main__":
    demo_spacy_detection()