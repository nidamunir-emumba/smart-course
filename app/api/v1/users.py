"""User & role management (student / instructor / admin). STUB — wire to services."""
from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def register_user():
    """Register a user with a role. TODO: persist via app.models.User."""
    raise NotImplementedError
