from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ReportCreate(BaseModel):
    questionnaire_answers: dict


class ReportOut(BaseModel):
    id: int
    created_at: str
    risk_level: str
    confidence: str
    questionnaire_input: dict
    portfolio_result: dict
    shap_result: dict | None = None
    lime_result: dict | None = None

class Config:
        from_attributes = True


class ReportSummary(BaseModel):
    id: int
    created_at: str
    risk_level: str
    confidence: str

class Config:
        from_attributes = True

class InvestmentPlanRequest(BaseModel):
    amount: float