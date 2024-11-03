"""Router para gerenciar músicas."""

from fastapi import APIRouter

router = APIRouter(
    prefix="/music",
    tags=["music"],
    responses={404: {"description": "Not found"}},
)

