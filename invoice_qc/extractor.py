import re
import datetime
import logging
from typing import List, Dict, Optional, Any
import pdfplumber

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_fields(text: str) -> Dict[str, Any]:
    """
    Extracts structured invoice data from raw text using regex and heuristics.
    """
    data = {
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "seller_name": None,
        "buyer_name": None,
        "currency": None,
        "net_total": None,
        "tax_amount": None,
        "gross_total": None,
        "line_items": []
    }

    def to_float(val):
        if not val: return None
        try:
            return float(val.replace(',', '').replace(' ', ''))
        except:
            return None

    # --- 1. Invoice Number ---
    # Look for "Invoice #" followed by some ID
    inv_num_match = re.search(r"(?i)(?:invoice\s*(?:no\.?|number|#)|inv\.?)\s*[:#]?\s*([a-zA-Z0-9\-\/]+)", text)
    if inv_num_match:
        data["invoice_number"] = inv_num_match.group(1).strip()

    # --- 2. Dates ---
    # Common date formats: DD/MM/YYYY, YYYY-MM-DD, Month DD, YYYY
    date_pattern = r"(?i)(?:date|dated|due)\s*[:]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})"
    
    dates_found = list(re.finditer(date_pattern, text))
    
    # Heuristic: First date usually Invoice Date, "Due" usually Due Date
    for match in dates_found:
        date_str = match.group(1)
        full_match = match.group(0).lower()
        
        # Simple normalization (skipping complex parsing for brevity)
        if "due" in full_match:
            data["due_date"] = date_str
        elif data["invoice_date"] is None:
            data["invoice_date"] = date_str

    # --- 3. Amounts & Currency ---
    # Currency symbols
    currency_map = {"$": "USD", "€": "EUR", "£": "GBP", "USD": "USD", "EUR": "EUR"}
    for symbol, code in currency_map.items():
        if symbol in text:
            data["currency"] = code
            break
            
    # Money pattern like 1,234.56 or 1234.56
    money_pattern = r"[\$€£]?\s*([\d,]+\.?\d{2})"
    
    # Net Total (Subtotal)
    net_match = re.search(r"(?i)(?:sub\s*total|net\s*amount|taxable\s*value)\s*[:]?\s*" + money_pattern, text)
    if net_match:
        data["net_total"] = to_float(net_match.group(1))

    # Tax Amount
    tax_match = re.search(r"(?i)(?:tax|vat|gst)\s*(?:total|amount)?\s*[:]?\s*" + money_pattern, text)
    if tax_match:
        data["tax_amount"] = to_float(tax_match.group(1))
        
    # Gross Total (Total Due)
    total_match = re.search(r"(?i)(?:total|amount\s*due|grand\s*total)\s*[:]?\s*" + money_pattern, text)
    if total_match:
        data["gross_total"] = to_float(total_match.group(1))

    return data

def extract_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Reads a PDF invoice and extracts structured data.
    """
    invoices_data = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Simple assumption: 1 PDF = 1 Invoice, possibly multi-page. 
            # We'll concatenate text for simple extraction.
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            extracted_data = extract_fields(full_text)
            
            # --- 4. Names (Heuristics) ---
            # Very naive heuristic: First non-empty lines are often Seller
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            if lines:
                extracted_data["seller_name"] = lines[0] # Assumption: First line is seller logo/name
            
            # "Bill To" usually precedes Buyer
            bill_to_idx = -1
            for i, line in enumerate(lines):
                if re.search(r"(?i)bill\s*to", line):
                    bill_to_idx = i
                    break
            
            if bill_to_idx != -1 and bill_to_idx + 1 < len(lines):
                extracted_data["buyer_name"] = lines[bill_to_idx + 1]

            invoices_data.append(extracted_data)
            
    except Exception as e:
        logger.error(f"Failed to process PDF {pdf_path}: {e}")
        return []

    return invoices_data

if __name__ == "__main__":
    # Example usage for quick testing if user runs this directly
    import sys
    import json
    
    if len(sys.argv) > 1:
        result = extract_from_pdf(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python -m invoice_qc.extractor <path_to_invoice.pdf>")
