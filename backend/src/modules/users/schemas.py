from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    display_name: str
    is_friend: bool = False
    can_surprise: bool = False
