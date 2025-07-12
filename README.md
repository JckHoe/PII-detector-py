# PII Detection and Anonymization Tools

Comprehensive PII (Personally Identifiable Information) detection and anonymization using multiple approaches: Regex, Presidio, and spaCy NER.

## Features

- **Multiple Detection Methods**: Regex, Presidio, spaCy NER
- **Fast Performance**: 60ms anonymization, 365ms detection
- **Memory Efficient**: <1MB memory usage for typical text
- **CLI Tool**: STDIN/STDOUT binary for easy integration
- **Anonymization Strategies**: Adaptive, hash, mask, partial, placeholder
- **Export Formats**: JSON, CSV, summary
- **No LLM Required**: All processing is local

## Installation

### Using uv (recommended)

```bash
uv sync
uv run python -m spacy download en_core_web_sm
```

### Using pip (alternative)

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## CLI Usage

### Basic Usage

```bash
# Pipe text through CLI
echo "Contact John at john@email.com" | uv run python pii_cli.py

# With strategy selection
echo "Call me at (555) 123-4567" | uv run python pii_cli.py --strategy hash

# With metrics
echo "My SSN is 123-45-6789" | uv run python pii_cli.py --metrics

# JSON output
echo "Visit https://example.com" | uv run python pii_cli.py --json
```

### CLI Options

```bash
Options:
  --strategy, -s    Anonymization strategy [adaptive|hash|placeholder|mask|partial]
  --detectors, -d   Which detectors to use [all|regex|presidio|spacy]
  --metrics, -m     Show performance metrics on stderr
  --json, -j        Output results as JSON
  --quiet, -q       Suppress warning messages
  --input, -i       Input file (default: stdin)
  --output, -o      Output file (default: stdout)
```

### Examples

```bash
# Different strategies
echo "John Doe john@email.com (555) 123-4567" | uv run python pii_cli.py -s adaptive
# Output: J*** D*** jo***@email.com ***-***-4567

echo "John Doe john@email.com (555) 123-4567" | uv run python pii_cli.py -s hash  
# Output: [PERSON_NAME_abc123] [EMAIL_ADDRESS_def456] [PHONE_789xyz]

# File processing
uv run python pii_cli.py -i input.txt -o anonymized.txt --strategy mask

# JSON with metrics
echo "Contact info" | uv run python pii_cli.py --json --metrics
```

## Building Binary

```bash
# Build standalone binary
uv run python build_binary.py

# Use binary directly
echo "PII text here" | ./dist/pii-cli --strategy adaptive
```

## Library Usage

```python
from combined_pii_detector import CombinedPIIDetector

detector = CombinedPIIDetector()
text = "Contact John Doe at john.doe@email.com or (555) 123-4567"

# Detect PII
entities = detector.detect_pii(text)

# Anonymize text  
results = detector.anonymize_text(text, strategy='adaptive')
print(results['anonymized_text'])
# Output: Contact J*** D*** at jo***@email.com or ***-***-4567
```

## Performance Metrics

- **Detection**: ~365ms (combined approach)
- **Anonymization**: ~60ms per strategy
- **Memory**: <1MB for typical text processing
- **Accuracy**: High with combined regex + NLP approach

## PII Types Detected

- Email addresses
- Phone numbers  
- Social Security Numbers (SSN)
- Credit card numbers
- IP addresses
- URLs
- Person names
- Organizations
- Locations
- Dates and times
- US passport numbers
- Driver's license numbers

## Anonymization Strategies

1. **Adaptive**: Smart anonymization based on PII type and confidence
2. **Hash**: Replace with hash-based identifiers  
3. **Placeholder**: Replace with generic placeholders
4. **Mask**: Partially mask with asterisks
5. **Partial**: Show partial information (e.g., first/last characters)

## Individual Detectors

```bash
# Regex-based detection (fastest)
uv run python regex_pii_detector.py

# Presidio detection (most comprehensive)  
uv run python presidio_pii_detector.py

# spaCy NER detection (best for names/locations)
uv run python spacy_ner_pii_detector.py

# Combined approach (best accuracy)
uv run python combined_pii_detector.py
```

## Integration Examples

```bash
# Process log files
cat application.log | ./dist/pii-cli --strategy hash > anonymized.log

# Batch processing
find . -name "*.txt" -exec sh -c './dist/pii-cli -i "$1" -o "${1%.txt}_anon.txt"' _ {} \;

# API integration
curl -s api/data | ./dist/pii-cli --json --quiet | jq '.anonymized_text'
```

## Dependencies

- **spaCy**: NER and linguistic processing
- **Presidio**: Microsoft's PII detection framework  
- **PyInstaller**: Binary compilation
- **Python 3.8+**: Runtime requirement

No external APIs or LLMs required - all processing is local and fast.