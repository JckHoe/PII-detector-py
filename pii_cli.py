import argparse
from spacy_detector import SpacyNERPIIDetector

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PII Detection and Anonymization CLI",
        epilog="Example: echo 'Contact John at john@email.com' | pii-cli --local-model-path path_to_spacy_model"
    )
    
    parser.add_argument(
        "--local-model-path",
        type=str,
        help="Path to local spaCy model directory (overrides bundled model)"
    )
    
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.local_model_path is None:
        raise ValueError("Local model path is required. Use --local-model-path to specify the path to your spaCy model.")

    detector = SpacyNERPIIDetector(model_path=args.local_model_path)
    try:
        while True:
            line = input().strip()
            if not line:
                break
            result = detector.detect_pii_combined(line)
            print(result)
    except KeyboardInterrupt:
        return 130
    except FileNotFoundError:
        return 2
    except Exception:
        return 1

if __name__ == "__main__":
    main()

