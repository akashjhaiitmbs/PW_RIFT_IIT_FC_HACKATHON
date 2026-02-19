"""
GET /api/v1/supported-drugs
Returns the list of supported drugs and their primary genes.
"""
from fastapi import APIRouter
from app.services.cpic_engine import DRUG_TO_GENE
from app.schemas.schemas import APIResponse, SupportedDrugSchema

router = APIRouter()


@router.get("/supported-drugs", response_model=APIResponse[list])
async def supported_drugs():
    data = [
        {"drug": drug, "primary_gene": gene}
        for drug, gene in DRUG_TO_GENE.items()
    ]
    return APIResponse(success=True, data=data)


@router.get("/health")
async def health():
    return {"success": True, "data": {"status": "healthy"}, "error": None}
