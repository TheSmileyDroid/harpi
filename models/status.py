from typing import Literal
from pydantic import BaseModel


class IStatus(BaseModel):
    """Estado atual do Bot."""

    status: Literal["online", "offline"]
