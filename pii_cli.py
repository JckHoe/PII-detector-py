#!/usr/bin/env python3

import sys
import argparse
import json
import time
from typing import Optional

import os

def setup_spacy_model_path():
    """Setup spaCy model path for bundled binary"""
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        model_path = os.path.join(bundle_dir, 'en_core_web_sm')
        if os.path.exists(model_path):
            os.environ['SPACY_MODEL_PATH'] = model_path
            print(f"Using bundled spaCy model: {model_path}", file=sys.stderr)
    
setup_spacy_model_path()

from combined_pii_detector import CombinedPIIDetector

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PII Detection and Anonymization CLI",
        epilog="Example: echo 'Contact John at john@email.com' | pii-cli --strategy adaptive"
    )
    
    parser.add_argument(
        "--strategy", "-s",
        choices=["adaptive", "hash", "placeholder", "mask", "partial"],
        default="adaptive",
        help="Anonymization strategy (default: adaptive)"
    )
    
    parser.add_argument(
        "--detectors", "-d",
        choices=["all", "regex", "presidio", "spacy"],
        default="all",
        help="Which detectors to use (default: all)"
    )
    
    parser.add_argument(
        "--metrics", "-m",
        action="store_true",
        help="Output performance metrics to stderr"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress warning messages"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input file (default: stdin)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file (default: stdout)"
    )
    
    parser.add_argument(
        "--interactive", 
        action="store_true",
        help="Interactive mode - continuously read from stdin"
    )
    
    return parser

def setup_detector(detectors: str, quiet: bool = False) -> CombinedPIIDetector:
    if detectors == "all":
        use_regex = use_presidio = use_spacy = True
    else:
        use_regex = detectors == "regex"
        use_presidio = detectors == "presidio"
        use_spacy = detectors == "spacy"
    
    import io
    import contextlib
    
    # Always suppress output during detector initialization in CLI
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        detector = CombinedPIIDetector(
            use_regex=use_regex,
            use_presidio=use_presidio,
            use_spacy=use_spacy
        )
    
    return detector

def process_text(
    text: str,
    detector: CombinedPIIDetector,
    strategy: str,
    output_json: bool = False,
    show_metrics: bool = False
) -> str:
    start_time = time.perf_counter()
    
    results = detector.anonymize_text(text.strip(), strategy)
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    if show_metrics:
        metrics_info = {
            "total_time": total_time,
            "detection_time": results["metrics"]["detection"]["execution_time"],
            "anonymization_time": results["metrics"]["anonymization"]["execution_time"],
            "memory_peak_mb": results["metrics"]["detection"]["memory_peak_mb"],
            "entities_found": len(results["entities"])
        }
        print(f"Metrics: {json.dumps(metrics_info)}", file=sys.stderr)
    
    if output_json:
        output_data = {
            "anonymized_text": results["anonymized_text"],
            "entities_found": len(results["entities"]),
            "strategy": strategy
        }
        if show_metrics:
            output_data["metrics"] = metrics_info
        
        return json.dumps(output_data, indent=2)
    else:
        return results["anonymized_text"]

def interactive_mode(detector: CombinedPIIDetector, args):
    """Interactive mode - continuously read from stdin and output results"""
    if not args.quiet:
        print("Interactive PII Detection Mode. Enter text (Ctrl+C to exit):", file=sys.stderr)
    
    try:
        while True:
            try:
                line = input()
                if line.strip():
                    result = process_text(
                        line,
                        detector,
                        args.strategy,
                        args.json,
                        args.metrics
                    )
                    print(result)
                    sys.stdout.flush()
            except EOFError:
                break
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nExiting interactive mode", file=sys.stderr)

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        detector = setup_detector(args.detectors, args.quiet)
        
        if args.interactive:
            interactive_mode(detector, args)
            return 0
        
        if args.input:
            with open(args.input, 'r', encoding='utf-8') as f:
                input_text = f.read()
        else:
            input_text = sys.stdin.read()
        
        if not input_text.strip():
            if not args.quiet:
                print("Warning: No input text provided", file=sys.stderr)
            return 0
        
        result = process_text(
            input_text,
            detector,
            args.strategy,
            args.json,
            args.metrics
        )
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
        else:
            print(result)
        
        return 0
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nInterrupted by user", file=sys.stderr)
        return 130
    except FileNotFoundError as e:
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
