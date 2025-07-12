import json
import time
import tracemalloc
from typing import Dict, List, Optional, Union, NamedTuple
from dataclasses import dataclass
import hashlib

from regex_pii_detector import RegexPIIDetector
try:
    from presidio_pii_detector import PresidioPIIDetector
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    print("Presidio not available. Install with: pip install presidio-analyzer presidio-anonymizer")

try:
    from spacy_ner_pii_detector import SpacyNERPIIDetector
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")

class Metrics(NamedTuple):
    execution_time: float
    memory_peak_mb: float
    memory_current_mb: float

@dataclass
class PIIEntity:
    entity_type: str
    text: str
    start: int
    end: int
    confidence: float
    source: str
    anonymized_value: Optional[str] = None

class CombinedPIIDetector:
    def __init__(self, use_regex: bool = True, use_presidio: bool = True, use_spacy: bool = True):
        self.detectors = {}
        
        if use_regex:
            self.detectors['regex'] = RegexPIIDetector()
        
        if use_presidio and PRESIDIO_AVAILABLE:
            self.detectors['presidio'] = PresidioPIIDetector()
        
        if use_spacy and SPACY_AVAILABLE:
            self.detectors['spacy'] = SpacyNERPIIDetector()
        
        print(f"Initialized detectors: {list(self.detectors.keys())}")
    
    def detect_pii(self, text: str) -> List[PIIEntity]:
        tracemalloc.start()
        start_time = time.perf_counter()
        
        all_entities = []
        
        if 'regex' in self.detectors:
            regex_results = self.detectors['regex'].detect_pii(text)
            for pii_type, matches in regex_results.items():
                for match_text, start, end in matches:
                    all_entities.append(PIIEntity(
                        entity_type=pii_type,
                        text=match_text,
                        start=start,
                        end=end,
                        confidence=0.8,
                        source='regex'
                    ))
        
        if 'presidio' in self.detectors:
            presidio_results = self.detectors['presidio'].detect_pii(text)
            for result in presidio_results:
                all_entities.append(PIIEntity(
                    entity_type=result['entity_type'].lower(),
                    text=result['text'],
                    start=result['start'],
                    end=result['end'],
                    confidence=result['confidence'],
                    source='presidio'
                ))
        
        if 'spacy' in self.detectors:
            spacy_results = self.detectors['spacy'].detect_pii_combined(text)
            for result in spacy_results:
                all_entities.append(PIIEntity(
                    entity_type=result['entity_type'],
                    text=result['text'],
                    start=result['start'],
                    end=result['end'],
                    confidence=result['confidence'],
                    source='spacy'
                ))
        
        merged_entities = self._merge_entities(all_entities)
        
        detected_values = [entity.text for entity in merged_entities]
        print(json.dumps(detected_values))
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_detection_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return merged_entities
    
    def _merge_entities(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        if not entities:
            return []
        
        entities.sort(key=lambda x: x.start)
        
        merged = []
        current = entities[0]
        
        for next_entity in entities[1:]:
            if (next_entity.start <= current.end and 
                next_entity.end >= current.start):
                
                if next_entity.confidence > current.confidence:
                    current = PIIEntity(
                        entity_type=next_entity.entity_type,
                        text=next_entity.text,
                        start=min(current.start, next_entity.start),
                        end=max(current.end, next_entity.end),
                        confidence=next_entity.confidence,
                        source=f"{current.source}+{next_entity.source}"
                    )
                else:
                    current = PIIEntity(
                        entity_type=current.entity_type,
                        text=current.text,
                        start=min(current.start, next_entity.start),
                        end=max(current.end, next_entity.end),
                        confidence=current.confidence,
                        source=f"{current.source}+{next_entity.source}"
                    )
            else:
                merged.append(current)
                current = next_entity
        
        merged.append(current)
        return merged
    
    def anonymize_text(self, text: str, strategy: str = 'adaptive') -> Dict:
        tracemalloc.start()
        start_time = time.perf_counter()
        
        entities = self.detect_pii(text)
        anonymized_text = text
        mapping = {}
        
        entities_sorted = sorted(entities, key=lambda x: x.start, reverse=True)
        
        for entity in entities_sorted:
            original = entity.text
            entity_type = entity.entity_type
            
            if strategy == 'adaptive':
                anonymized = self._adaptive_anonymization(entity)
            elif strategy == 'hash':
                anonymized = f"[{entity_type.upper()}_{hashlib.md5(original.encode()).hexdigest()[:8]}]"
            elif strategy == 'placeholder':
                anonymized = f"[{entity_type.upper()}_REDACTED]"
            elif strategy == 'mask':
                if len(original) > 4:
                    anonymized = original[:2] + '*' * (len(original) - 4) + original[-2:]
                else:
                    anonymized = '*' * len(original)
            else:
                anonymized = f"[{entity_type.upper()}_REDACTED]"
            
            entity.anonymized_value = anonymized
            
            if anonymized is not None:
                anonymized_text = (anonymized_text[:entity.start] + 
                                 anonymized + 
                                 anonymized_text[entity.end:])
            
            mapping[original] = anonymized
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.last_anonymize_metrics = Metrics(
            execution_time=end_time - start_time,
            memory_peak_mb=peak / 1024 / 1024,
            memory_current_mb=current / 1024 / 1024
        )
        
        return {
            'original_text': text,
            'anonymized_text': anonymized_text,
            'entities': entities,
            'mapping': mapping,
            'stats': self._get_stats(entities),
            'metrics': {
                'detection': self.last_detection_metrics._asdict(),
                'anonymization': self.last_anonymize_metrics._asdict()
            }
        }
    
    def _adaptive_anonymization(self, entity: PIIEntity) -> str:
        original = entity.text
        entity_type = entity.entity_type
        confidence = entity.confidence
        
        if confidence > 0.9:
            if entity_type in ['email', 'email_address']:
                parts = original.split('@')
                if len(parts) == 2:
                    return f"{parts[0][:2]}***@{parts[1]}"
            elif entity_type in ['phone', 'phone_number']:
                return f"***-***-{original[-4:]}"
            elif entity_type in ['person', 'person_name']:
                words = original.split()
                if len(words) > 1:
                    return f"{words[0][0]}*** {words[-1][0]}***"
                else:
                    return f"{original[0]}***"
            elif entity_type == 'credit_card':
                return f"****-****-****-{original[-4:]}"
        
        elif confidence > 0.7:
            return f"[{entity_type.upper()}_{hashlib.md5(original.encode()).hexdigest()[:6]}]"
        
        else:
            return f"[{entity_type.upper()}_POSSIBLE]"
    
    def _get_stats(self, entities: List[PIIEntity]) -> Dict:
        stats = {
            'total_entities': len(entities),
            'entity_types': {},
            'sources': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        for entity in entities:
            if entity.entity_type not in stats['entity_types']:
                stats['entity_types'][entity.entity_type] = 0
            stats['entity_types'][entity.entity_type] += 1
            
            if entity.source not in stats['sources']:
                stats['sources'][entity.source] = 0
            stats['sources'][entity.source] += 1
            
            if entity.confidence > 0.8:
                stats['confidence_distribution']['high'] += 1
            elif entity.confidence > 0.6:
                stats['confidence_distribution']['medium'] += 1
            else:
                stats['confidence_distribution']['low'] += 1
        
        return stats
    
    def export_results(self, results: Dict, format: str = 'json') -> str:
        if format == 'json':
            exportable = {
                'original_text': results['original_text'],
                'anonymized_text': results['anonymized_text'],
                'entities': [
                    {
                        'entity_type': e.entity_type,
                        'text': e.text,
                        'start': e.start,
                        'end': e.end,
                        'confidence': e.confidence,
                        'source': e.source,
                        'anonymized_value': e.anonymized_value
                    } for e in results['entities']
                ],
                'mapping': results['mapping'],
                'stats': results['stats']
            }
            return json.dumps(exportable, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Entity Type', 'Original Text', 'Start', 'End', 'Confidence', 'Source', 'Anonymized'])
            
            for entity in results['entities']:
                writer.writerow([
                    entity.entity_type,
                    entity.text,
                    entity.start,
                    entity.end,
                    entity.confidence,
                    entity.source,
                    entity.anonymized_value
                ])
            
            return output.getvalue()
        
        elif format == 'summary':
            lines = [
                f"PII Detection Summary",
                f"=" * 20,
                f"Total entities found: {results['stats']['total_entities']}",
                f"Entity types: {', '.join(results['stats']['entity_types'].keys())}",
                f"Detection sources: {', '.join(results['stats']['sources'].keys())}",
                f"",
                f"Confidence distribution:",
                f"  High (>0.8): {results['stats']['confidence_distribution']['high']}",
                f"  Medium (0.6-0.8): {results['stats']['confidence_distribution']['medium']}",
                f"  Low (<0.6): {results['stats']['confidence_distribution']['low']}"
            ]
            return "\n".join(lines)

def demo_combined_detection():
    detector = CombinedPIIDetector()
    
    sample_text = """
    Dear Dr. Sarah Johnson,
    
    Thank you for your inquiry. My email is contact@hospital.com and you can reach me at (555) 123-4567.
    Your patient John Smith (DOB: 1985-03-15, SSN: 123-45-6789) has an appointment scheduled.
    
    The consultation fee is $150 and can be paid by credit card (4532 1234 5678 9012).
    Our clinic is located at 123 Medical Center Drive, Boston, MA 02101.
    
    Please visit our website at https://medical-center.com for more information.
    The appointment confirmation number is #MC123456.
    
    Best regards,
    Dr. Michael Davis
    Chief Medical Officer
    Boston Medical Center
    """
    
    print("=== Combined PII Detection Demo ===\n")
    print("Original text:")
    print(sample_text)
    print("\n" + "="*60)
    
    entities = detector.detect_pii(sample_text)
    print(f"\nDetected {len(entities)} PII entities:")
    for entity in entities:
        print(f"- {entity.entity_type}: '{entity.text}' "
              f"(confidence: {entity.confidence:.2f}, source: {entity.source})")
    
    print(f"\nDetection Metrics:")
    print(f"Time: {detector.last_detection_metrics.execution_time:.4f} seconds")
    print(f"Memory Peak: {detector.last_detection_metrics.memory_peak_mb:.2f} MB")
    print(f"Memory Current: {detector.last_detection_metrics.memory_current_mb:.2f} MB")
    
    print("\n" + "="*60)
    
    strategies = ['adaptive', 'hash', 'placeholder', 'mask']
    for strategy in strategies:
        results = detector.anonymize_text(sample_text, strategy)
        print(f"\nAnonymized text ({strategy} strategy):")
        print(results['anonymized_text'][:200] + "..." if len(results['anonymized_text']) > 200 else results['anonymized_text'])
        print(f"Anonymization Metrics ({strategy}):")
        print(f"  Time: {results['metrics']['anonymization']['execution_time']:.4f}s")
        print(f"  Memory Peak: {results['metrics']['anonymization']['memory_peak_mb']:.2f} MB")
    
    print("\n" + "="*60)
    
    results = detector.anonymize_text(sample_text, 'adaptive')
    
    print("\nDetailed Results:")
    print(detector.export_results(results, 'summary'))
    
    print("\n" + "="*60)
    print("\nJSON Export (first 500 chars):")
    json_export = detector.export_results(results, 'json')
    print(json_export[:500] + "..." if len(json_export) > 500 else json_export)

if __name__ == "__main__":
    demo_combined_detection()
