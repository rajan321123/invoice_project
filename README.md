# B2B Invoice QC System: Extraction Schema & Validation Rules

This document outlines the data extraction schema and quality control validation rules for the B2B Invoice Processing System.


## Software Overview

[Watch the Software Overview Video](https://drive.google.com/file/d/11vTHELEXiWYfZeNeKG4Z4KNvt5i1-M-a/view?usp=share_link)

## 1. Invoice Extraction Schema

The following 10 fields are extracted from each invoice document:

| Field Name | Data Type | Description | Example |
| :--- | :--- | :--- | :--- |
| **Invoice Number** | String | Unique identifier assigned by the vendor to the invoice. | `INV-2023-001` |
| **Invoice Date** | Date (ISO 8601) | The date the invoice was issued. | `2023-10-27` |
| **Vendor Name** | String | The legal name of the entity issuing the invoice. | `Acme Corp.` |
| **Vendor Tax ID** | String | Tax identification number of the vendor (e.g., VAT, EIN, GST). | `US12-3456789` |
| **Buyer Name** | String | The name of the entity receiving the invoice. | `Global Industries Ltd.` |
| **Purchase Order (PO) Number** | String | Reference number for the purchase order related to the invoice. | `PO-998877` |
| **Currency Code** | String (ISO 4217) | The currency in which the invoice is issued. | `USD`, `EUR` |
| **Total Net Amount** | Decimal | Total amount before taxes and discounts. | `1000.00` |
| **Total Tax Amount** | Decimal | Total tax amount applied to the invoice. | `150.00` |
| **Total Amount Due** | Decimal | The final amount payable, including taxes and adjustments. | `1150.00` |

---

## 2. Quality Validation Rules

The system applies the following rules to ensure data quality and integrity.

### A. Completeness Rules (Critical)
These rules ensure that essential information is present for the invoice to be processed.

1.  **Mandatory Field Check**:
    *   **Rule**: `Invoice Number` and `Total Amount Due` must not be null or empty.
    *   **Action**: Flag invoice as `REJECTED` if any are missing. `Invoice Date` and `Vendor Name` missing will result in a `WARNING`.

2.  **Vendor Identification Check**:
    *   **Rule**: At least one of `Vendor Tax ID` OR `Vendor Address` must be present (if Tax ID is missing).
    *   **Action**: Flag for `MANUAL_REVIEW` if identification is insufficient.

3.  **Line Item Extraction Check**:
    *   **Rule**: The extraction output must contain at least one line item (even if line items are not detailed in the schema above, the system validates their existence).
    *   **Action**: Flag for `MANUAL_REVIEW` if no line items are detected but `Total Amount Due` > 0.

### B. Business Consistency Rules
These rules validate the logical consistency of the extracted data.

4.  **Arithmetic Reconciliation**:
    *   **Rule**: `Total Net Amount` + `Total Tax Amount` must equal `Total Amount Due` (within a tolerance of ±0.05 currency units).
    *   **Action**: Flag for `WARNING` if the sum does not match.

5.  **Date Logical Validity**:
    *   **Rule**: `Invoice Date` cannot be in the future (relative to the extraction timestamp) AND strictly not older than 365 days.
    *   **Action**: Flag for `WARNING` if date is invalid to prevent processing stale or incorrect future invoices.

### C. Anomaly & Duplicate Rules
These rules detect potential fraud or processing errors.

6.  **Duplicate Invoice Check**:
    This is a compound unique check to prevent double payment.
    *   **Rule**: The combination of `Vendor Tax ID` + `Invoice Number` + `Fiscal Year` must be unique in the database.
    *   **Action**: Flag invoice as `DUPLICATE` and halt processing if a match is found.
