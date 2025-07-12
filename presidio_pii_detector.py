from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import hashlib
import time
import tracemalloc
from typing import Dict, List, NamedTuple

class Metrics(NamedTuple):
    execution_time: float
    memory_peak_mb: float
    memory_current_mb: float

class PresidioPIIDetector:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        self.entity_types = [
            "CREDIT_CARD", "CRYPTO", "DATE_TIME", "EMAIL_ADDRESS", 
            "IBAN_CODE", "IP_ADDRESS", "NRP", "LOCATION", "PERSON", 
            "PHONE_NUMBER", "MEDICAL_LICENSE", "URL", "US_BANK_NUMBER", 
            "US_DRIVER_LICENSE", "US_ITIN", "US_PASSPORT", "US_SSN"
        ]
    
    def detect_pii(self, text: str, language: str = "en") -> List[Dict]:
        tracemalloc.start()
        start_time = time.perf_counter()
        
        results = self.analyzer.analyze(
            text=text,
            entities=self.entity_types,
            language=language
        )
        
        pii_found = []
        for result in results:
            pii_found.append({
                'entity_type': result.entity_type,
                'text': text[result.start:result.end],
                'start': result.start,
                'end': result.end,
                'confidence': result.score
            })
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return pii_found
    
    def anonymize_text(self, text: str, strategy: str = "replace", language: str = "en") -> Dict:
        tracemalloc.start()
        start_time = time.perf_counter()
        
        analyzer_results = self.analyzer.analyze(
            text=text,
            entities=self.entity_types,
            language=language
        )
        
        if strategy == "replace":
            operators = {"DEFAULT": OperatorConfig("replace")}
        elif strategy == "redact":
            operators = {"DEFAULT": OperatorConfig("redact")}
        elif strategy == "hash":
            operators = {"DEFAULT": OperatorConfig("hash")}
        elif strategy == "mask":
            operators = {"DEFAULT": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*"})}
        elif strategy == "custom":
            operators = {
                "PHONE_NUMBER": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
                "PERSON": OperatorConfig("replace", {"new_value": "[NAME_REDACTED]"}),
                "CREDIT_CARD": OperatorConfig("mask", {"chars_to_mask": 12, "masking_char": "*"}),
                "DEFAULT": OperatorConfig("redact")
            }
        else:
            operators = {"DEFAULT": OperatorConfig("replace")}
        
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators
        )
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_anonymize_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return {
            'anonymized_text': anonymized_result.text,
            'items': [
                {
                    'entity_type': item.entity_type,
                    'start': item.start,
                    'end': item.end,
                    'text': item.text,
                    'operator': item.operator
                }
                for item in anonymized_result.items
            ]
        }
    
    def get_entity_mapping(self, text: str, language: str = "en") -> Dict[str, str]:
        detected = self.detect_pii(text, language)
        anonymized = self.anonymize_text(text, "hash", language)
        
        mapping = {}
        for i, detection in enumerate(detected):
            if i < len(anonymized['items']):
                mapping[detection['text']] = anonymized['items'][i]['text']
        
        return mapping

def demo_presidio_detection():
    try:
        detector = PresidioPIIDetector()
        
        sample_text = """
        Hi Sarah Johnson, my email is sarah.johnson@company.com and my phone is (555) 123-4567.
        My SSN is 123-45-6789 and I live in New York City.
        My credit card number is 4532 1234 5678 9012.
        I was born on 1985-03-15 and my passport is AB1234567.
        Visit my profile at https://linkedin.com/in/sarahjohnson
        """
        
        print("Original text:")
        print(sample_text)
        print("\n" + "="*60)
        
        detected_pii = detector.detect_pii(sample_text)
        print("\nDetected PII:")
        for pii in detected_pii:
            print(f"- {pii['entity_type']}: '{pii['text']}' (confidence: {pii['confidence']:.2f})")
        
        print(f"\nDetection Metrics:")
        print(f"Time: {detector.last_metrics.execution_time:.4f} seconds")
        print(f"Memory Peak: {detector.last_metrics.memory_peak_mb:.2f} MB")
        print(f"Memory Current: {detector.last_metrics.memory_current_mb:.2f} MB")
        
        print("\n" + "="*60)
        
        strategies = ['replace', 'redact', 'hash', 'mask', 'custom']
        for strategy in strategies:
            result = detector.anonymize_text(sample_text, strategy)
            print(f"\nAnonymized text ({strategy} strategy):")
            print(result['anonymized_text'])
            print(f"Anonymization Metrics ({strategy}):")
            print(f"  Time: {detector.last_anonymize_metrics.execution_time:.4f}s")
            print(f"  Memory Peak: {detector.last_anonymize_metrics.memory_peak_mb:.2f} MB")
        
        print("\n" + "="*60)
        
        mapping = detector.get_entity_mapping(sample_text)
        print("\nEntity Mapping (original -> anonymized):")
        for original, anonymized in mapping.items():
            print(f"'{original}' -> '{anonymized}'")
            
    except ImportError as e:
        print(f"Please install presidio: pip install presidio-analyzer presidio-anonymizer")
        print(f"Error: {e}")

if __name__ == "__main__":
    demo_presidio_detection()