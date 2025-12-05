import os
import shutil
import tempfile
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from invoice_qc import extractor
from invoice_qc import validator

app = FastAPI(title="Invoice QC API", description="API for extracting and validating B2B invoices.")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for validation
class ValidationRequest(BaseModel):
    invoices: List[Dict[str, Any]]

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/validate-json")
def validate_json(request: ValidationRequest):
    """
    Validates a list of already extracted invoice JSON objects.
    """
    if not request.invoices:
        raise HTTPException(status_code=400, detail="No invoices provided.")
    
    report = validator.validate_batch(request.invoices)
    return report

@app.post("/extract-and-validate-pdfs")
def extract_and_validate_pdfs(files: List[UploadFile] = File(...)):
    """
    Uploads PDF files, extracts data, and runs validation.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    all_invoices = []
    
    # Create a temporary directory to store uploaded files for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                continue
                
            temp_path = os.path.join(temp_dir, file.filename)
            
            try:
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                # Extract
                invoices = extractor.extract_from_pdf(temp_path)
                all_invoices.extend(invoices)
                
            except Exception as e:
                # In a real app, we might want to return partial errors, 
                # but here we log and continue or could raise.
                # For now, we'll just skip failed files or add a placeholder error.
                pass
            finally:
                file.file.close()

    if not all_invoices:
        return {
            "summary": {"total_processed": 0, "approved": 0, "warnings": 0, "rejected": 0},
            "details": [],
            "message": "No valid data extracted from uploaded files."
        }

    # Validate
    report = validator.validate_batch(all_invoices)
    return report

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
