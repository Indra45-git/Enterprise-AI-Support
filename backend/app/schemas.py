from pydantic import BaseModel, Field, field_validator


class OrderIdArg(BaseModel):
    order_id: str = Field(..., pattern=r"^ORD\d{4,6}$")

    @field_validator("order_id", mode="before")
    @classmethod
    def normalize_order_id(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v


class ProductIdArg(BaseModel):
    product_id: str = Field(..., pattern=r"^PROD\d{3,6}$")

    @field_validator("product_id", mode="before")
    @classmethod
    def normalize_product_id(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v


class ReturnEligibilityArgs(BaseModel):
    order_id: str = Field(..., pattern=r"^ORD\d{4,6}$")
    product_id: str = Field(..., pattern=r"^PROD\d{3,6}$")

    @field_validator("order_id", mode="before")
    @classmethod
    def normalize_order_id(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v

    @field_validator("product_id", mode="before")
    @classmethod
    def normalize_product_id(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v


class TicketIdArg(BaseModel):
    ticket_id: str

    @field_validator("ticket_id", mode="before")
    @classmethod
    def not_empty(cls, v):
        if not v or not str(v).strip():
            raise ValueError("ticket_id required")
        return str(v).strip().upper()


class CreateTicketArgs(BaseModel):
    issue_type: str
    description: str = Field(..., min_length=3, max_length=2000)
    order_id: str | None = Field(default=None, pattern=r"^ORD\d{4,6}$")

    @field_validator("order_id", mode="before")
    @classmethod
    def normalize_order_id(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip().upper()


class EscalateTicketArgs(BaseModel):
    ticket_id: str
    reason: str = Field(..., min_length=3, max_length=500)

    @field_validator("ticket_id", mode="before")
    @classmethod
    def normalize_ticket_id(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v



class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    bot_id: str | None = None


class ChatbotSettingsUpdate(BaseModel):
    bot_name: str | None = None
    welcome_message: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    avatar_icon: str | None = None
    placeholder_text: str | None = None
    suggested_questions: str | None = None
    system_instructions: str | None = None
    is_public: bool | None = None

