import re
import hashlib
import time
import tracemalloc
from typing import Dict, List, Tuple, NamedTuple

class Metrics(NamedTuple):
    execution_time: float
    memory_peak_mb: float
    memory_current_mb: float

class RegexPIIDetector:
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            'us_passport': r'\b[A-Z]{1,2}\d{6,9}\b',
            'drivers_license': r'\b[A-Z]\d{7,8}\b'
        }
    
    def detect_pii(self, text: str) -> Dict[str, List[Tuple[str, int, int]]]:
        tracemalloc.start()
        start_time = time.perf_counter()
        
        results = {}
        
        for pii_type, pattern in self.patterns.items():
            matches = []
            for match in re.finditer(pattern, text):
                matches.append((match.group(), match.start(), match.end()))
            if matches:
                results[pii_type] = matches
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return results
    
    def anonymize_text(self, text: str, replacement_strategy: str = 'hash') -> Tuple[str, Dict]:
        tracemalloc.start()
        start_time = time.perf_counter()
        
        anonymized_text = text
        mapping = {}
        
        pii_found = self.detect_pii(text)
        
        for pii_type, matches in pii_found.items():
            for original_value, start, end in matches:
                if replacement_strategy == 'hash':
                    anonymized = f"[{pii_type.upper()}_{hashlib.md5(original_value.encode()).hexdigest()[:8]}]"
                elif replacement_strategy == 'placeholder':
                    anonymized = f"[{pii_type.upper()}_REDACTED]"
                elif replacement_strategy == 'partial':
                    if pii_type == 'email':
                        parts = original_value.split('@')
                        anonymized = f"{parts[0][:2]}***@{parts[1]}"
                    elif pii_type == 'phone':
                        anonymized = f"***-***-{original_value[-4:]}"
                    else:
                        anonymized = f"[{pii_type.upper()}_REDACTED]"
                else:
                    anonymized = f"[{pii_type.upper()}_REDACTED]"
                
                anonymized_text = anonymized_text.replace(original_value, anonymized)
                mapping[anonymized] = original_value
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_anonymize_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return anonymized_text, mapping

def demo_regex_detection():
    detector = RegexPIIDetector()
    
    sample_text = """
    Hi John, my email is john.doe@example.com and my phone number is (555) 123-4567.
    My SSN is 123-45-6789 and credit card is 4532 1234 5678 9012.
    You can visit my website at https://johndoe.com or call me at 555.987.6543.
    My passport number is AB1234567.
    """
    
    print("Original text:")
    print(sample_text)
    print("\n" + "="*50)
    
    pii_found = detector.detect_pii(sample_text)
    print("\nPII Detection Results:")
    for pii_type, matches in pii_found.items():
        print(f"{pii_type}: {[match[0] for match in matches]}")
    
    print(f"\nDetection Metrics:")
    print(f"Time: {detector.last_metrics.execution_time:.4f} seconds")
    print(f"Memory Peak: {detector.last_metrics.memory_peak_mb:.2f} MB")
    print(f"Memory Current: {detector.last_metrics.memory_current_mb:.2f} MB")
    
    print("\n" + "="*50)
    
    strategies = ['hash', 'placeholder', 'partial']
    for strategy in strategies:
        anonymized, mapping = detector.anonymize_text(sample_text, strategy)
        print(f"\nAnonymized text ({strategy} strategy):")
        print(anonymized)
        print(f"Anonymization Metrics ({strategy}):")
        print(f"  Time: {detector.last_anonymize_metrics.execution_time:.4f}s")
        print(f"  Memory Peak: {detector.last_anonymize_metrics.memory_peak_mb:.2f} MB")

if __name__ == "__main__":
    demo_regex_detection()