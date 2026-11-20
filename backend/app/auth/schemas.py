from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None = None
    email: str | None = None
    workspace_name: str | None = None