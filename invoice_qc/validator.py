import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional
import collections

# Type alias for clarity
Invoice = Dict[str, Any]
ValidationResult = Dict[str, Any]

def parse_amount(amount_str: Any) -> Optional[Decimal]:
    """Helper to parse amount strings to Decimal."""
    if amount_str is None:
        return None
    if isinstance(amount_str, (int, float, Decimal)):
        return Decimal(str(amount_str))
    
    try:
        # Remove currency symbols and commas
        clean_str = str(amount_str).replace(',', '').replace('$', '').replace('€', '').replace('£', '').strip()
        return Decimal(clean_str)
    except (InvalidOperation, ValueError):
        return None

def parse_date(date_str: Any) -> Optional[datetime.date]:
    """Helper to parse date strings."""
    if date_str is None:
        return None
    if isinstance(date_str, datetime.date):
        return date_str
    if isinstance(date_str, datetime.datetime):
        return date_str.date()

    # Try common formats
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
        "%d-%m-%Y", "%d-%b-%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(str(date_str), fmt).date()
        except ValueError:
            continue
    return None

def validate_invoice(invoice: Invoice, history: List[Invoice] = []) -> ValidationResult:
    """
    Validates a single invoice against QC rules.
    
    Args:
        invoice: The invoice data dict.
        history: List of previously processed invoices (including current batch predecessors) for duplicate checking.
        
    Returns:
        Dict containing status, is_valid boolean, and list of errors/warnings.
    """
    errors = []
    warnings = []
    
    # --- 1. Completeness Checks ---
    # Relaxed Rules: Only Invoice Number and Gross Total are strictly mandatory for rejection.
    mandatory_critical = ["invoice_number", "gross_total"]
    for field in mandatory_critical:
        if not invoice.get(field):
            errors.append(f"Missing mandatory field: {field}")

    # Warn for other missing standard fields
    if not invoice.get("seller_name"):
        warnings.append("Missing seller_name")
    if not invoice.get("invoice_date"):
        warnings.append("Missing invoice_date")

    # --- 2. Type & Value Checks ---
    gross_total = parse_amount(invoice.get("gross_total"))
    net_total = parse_amount(invoice.get("net_total"))
    tax_amount = parse_amount(invoice.get("tax_amount"))
    invoice_date = parse_date(invoice.get("invoice_date"))

    if invoice.get("gross_total") and gross_total is None:
        errors.append("Invalid format for gross_total")
    if invoice.get("invoice_date") and invoice_date is None:
        warnings.append("Could not parse invoice_date")

    # --- 3. Business Consistency Rules ---
    
    # Arithmetic Reconciliation
    if gross_total is not None and net_total is not None and tax_amount is not None:
        calculated_total = net_total + tax_amount
        # Tolerance of 0.05
        if abs(calculated_total - gross_total) > Decimal("0.05"):
            warnings.append(f"Math mismatch: Net ({net_total}) + Tax ({tax_amount}) != Gross ({gross_total})")

    # Date Validity
    if invoice_date:
        today = datetime.date.today()
        if invoice_date > today:
            warnings.append(f"Invoice date {invoice_date} is in the future")
        elif (today - invoice_date).days > 365:
            warnings.append(f"Invoice date {invoice_date} is older than 365 days")

    # --- 4. Duplicate Check ---
    # Key: seller_name + invoice_number (normalized)
    current_key = (
        str(invoice.get("seller_name") or "").strip().lower(),
        str(invoice.get("invoice_number") or "").strip().lower()
    )
    
    if current_key[0] and current_key[1]:
        for past_inv in history:
            past_key = (
                str(past_inv.get("seller_name") or "").strip().lower(),
                str(past_inv.get("invoice_number") or "").strip().lower()
            )
            if current_key == past_key:
                errors.append(f"Duplicate invoice detected: {invoice.get('invoice_number')} from {invoice.get('seller_name')}")
                break

    # --- Determine Status ---
    is_valid = len(errors) == 0
    if not is_valid:
        status = "REJECTED"
    elif len(warnings) > 0:
        status = "WARNING"
    else:
        status = "APPROVED"

    return {
        "invoice_number": invoice.get("invoice_number"),
        "is_valid": is_valid,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "original_data": invoice
    }

def validate_batch(invoices: List[Invoice]) -> Dict[str, Any]:
    """
    Validates a batch of invoices.
    """
    results = []
    processed_history = []
    
    counts = collections.defaultdict(int)
    
    for inv in invoices:
        # Validate against history of THIS batch + potentially external history (not implemented here)
        result = validate_invoice(inv, history=processed_history)
        
        # Add to history if it has enough info to be a duplicate candidate
        if inv.get("invoice_number") and inv.get("seller_name"):
            processed_history.append(inv)
            
        results.append(result)
        counts[result["status"]] += 1
        
    return {
        "summary": {
            "total_processed": len(invoices),
            "approved": counts["APPROVED"],
            "warnings": counts["WARNING"],
            "rejected": counts["REJECTED"]
        },
        "details": results
    }

if __name__ == "__main__":
    # Test Data
    test_invoices = [
        {
            "invoice_number": "INV-001", "invoice_date": "2023-10-27", 
            "seller_name": "Acme", "gross_total": "1150.00", 
            "net_total": "1000.00", "tax_amount": "150.00"
        },
        {
            "invoice_number": "INV-002", "invoice_date": "2023-10-28", # Missing seller
            "gross_total": "500.00"
        },
        {
            "invoice_number": "INV-003", "invoice_date": "2023-10-29", 
            "seller_name": "Beta Corp", "gross_total": "100.00",
            "net_total": "80.00", "tax_amount": "10.00" # Math error 80+10 != 100
        },
        {
            "invoice_number": "INV-001", "invoice_date": "2023-10-27", # Duplicate
            "seller_name": "Acme", "gross_total": "1150.00"
        }
    ]
    
    import json
    report = validate_batch(test_invoices)
    print(json.dumps(report, indent=2, default=str))
