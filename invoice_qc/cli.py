import argparse
import json
import logging
import os
import sys
from typing import List

from invoice_qc import extractor
from invoice_qc import validator

# Configure logging to stderr so it doesn't pollute stdout JSON pipe if needed
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def cmd_extract(args):
    """Handles the extract command."""
    pdf_dir = args.pdf_dir
    output_path = args.output
    
    if not os.path.exists(pdf_dir):
        print(f"Error: Directory '{pdf_dir}' not found.")
        sys.exit(1)
        
    all_invoices = []
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    print(f"Found {len(pdf_files)} PDF files in {pdf_dir}...")
    
    for filename in pdf_files:
        path = os.path.join(pdf_dir, filename)
        print(f"Processing {filename}...", end=" ", flush=True)
        try:
            # extractor returns a list of invoices (usually 1)
            invoices = extractor.extract_from_pdf(path)
            all_invoices.extend(invoices)
            print("Done.")
        except Exception as e:
            print(f"Failed: {e}")
            
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(all_invoices, f, indent=2, default=str)
        print(f"Extracted data saved to {output_path}")
    else:
        print(json.dumps(all_invoices, indent=2, default=str))

def cmd_validate(args):
    """Handles the validate command."""
    input_path = args.input
    report_path = args.report
    
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)
        
    with open(input_path, 'r') as f:
        try:
            invoices = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Failed to parse JSON from '{input_path}'.")
            sys.exit(1)
            
    report = validator.validate_batch(invoices)
    
    # Console Summary
    summary = report['summary']
    print("\n--- Validation Summary ---")
    print(f"Total Processed: {summary['total_processed']}")
    print(f"Approved:        {summary['approved']}")
    print(f"Warnings:        {summary['warnings']}")
    print(f"Rejected:        {summary['rejected']}")
    print("--------------------------")
    
    if summary['rejected'] > 0:
        print("\nRejections:")
        for res in report['details']:
            if res['status'] == 'REJECTED':
                print(f"  - Invoice {res.get('invoice_number', 'Unknown')}: {', '.join(res['errors'])}")
    
    if report_path:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nFull validation report saved to {report_path}")
        
    if summary['rejected'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

def cmd_full_run(args):
    """Handles the full-run command."""
    pdf_dir = args.pdf_dir
    report_path = args.report
    
    if not os.path.exists(pdf_dir):
        print(f"Error: Directory '{pdf_dir}' not found.")
        sys.exit(1)

    # 1. Extraction
    all_invoices = []
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    print(f"--- Step 1: Extracting from {len(pdf_files)} PDFs ---")
    
    for filename in pdf_files:
        path = os.path.join(pdf_dir, filename)
        try:
            invoices = extractor.extract_from_pdf(path)
            all_invoices.extend(invoices)
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
    
    print(f"Extracted {len(all_invoices)} invoices.")
    
    # 2. Validation
    print("\n--- Step 2: Validating ---")
    report = validator.validate_batch(all_invoices)
    
    summary = report['summary']
    print(f"Approved: {summary['approved']}, Warnings: {summary['warnings']}, Rejected: {summary['rejected']}")
    
    if report_path:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to {report_path}")
        
    if summary['rejected'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Invoice QC System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Extract
    parser_extract = subparsers.add_parser("extract", help="Extract data from PDF invoices")
    parser_extract.add_argument("--pdf-dir", required=True, help="Directory containing PDF invoices")
    parser_extract.add_argument("--output", help="Path to save extracted JSON data")
    
    # Validate
    parser_validate = subparsers.add_parser("validate", help="Validate extracted invoice JSON data")
    parser_validate.add_argument("--input", required=True, help="Path to extracted JSON file")
    parser_validate.add_argument("--report", help="Path to save validation report JSON")
    
    # Full Run
    parser_full = subparsers.add_parser("full-run", help="Extract and validate in one go")
    parser_full.add_argument("--pdf-dir", required=True, help="Directory containing PDF invoices")
    parser_full.add_argument("--report", help="Path to save validation report JSON")
    
    args = parser.parse_args()
    
    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "full-run":
        cmd_full_run(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
