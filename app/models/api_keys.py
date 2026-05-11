from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import ENUM
from app.core.enums import APIUserTypeEnum
from app.models.base import CustomBaseModel
from sqlalchemy.sql.expression import text


class ApiKeysModel(CustomBaseModel):
    __tablename__ = "api_keys"
    id = Column(
        String, primary_key=True, index=True, server_default=text("gen_random_uuid()")
    )
    key_hash = Column(String, index=True, unique=True)
    type = Column(
        ENUM(APIUserTypeEnum),
        default=APIUserTypeEnum.PORTAL,
        server_default=APIUserTypeEnum.PORTAL,
    )
    name = Column(String)
    is_active = Column(Boolean, default=True, server_default="True")
    description = Column(Text, default="")
