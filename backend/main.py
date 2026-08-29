from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import json

from ml_bridge import run_full_pipeline
from datetime import timezone

from database import engine, Base, get_db
import models
import schemas
from security import hash_password, verify_password, create_access_token, get_current_user
from fastapi.middleware.cors import CORSMiddleware
from stock_prices import build_investment_plan
from portfolio_history import build_portfolio_history
from investment_reasoning import build_stock_reasoning, build_sector_reasoning

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Portfolio Recommendation System API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return schemas.Token(access_token=token)

@app.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/reports", response_model=schemas.ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: schemas.ReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    pipeline_result = run_full_pipeline(payload.questionnaire_answers)

    new_report = models.Report(
        user_id=current_user.id,
        risk_level=pipeline_result["risk_level"],
        confidence=str(pipeline_result["confidence"]),
        questionnaire_input=json.dumps(payload.questionnaire_answers),
        portfolio_result=json.dumps(pipeline_result["portfolio"]),
        shap_result=json.dumps(pipeline_result["shap"]),
        lime_result=json.dumps(pipeline_result["lime"]),
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return _report_to_out(new_report)


@app.get("/reports", response_model=list[schemas.ReportSummary])
def list_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    reports = (
        db.query(models.Report)
        .filter(models.Report.user_id == current_user.id)
        .order_by(models.Report.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "created_at": r.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "risk_level": r.risk_level,
            "confidence": r.confidence,
        }
        for r in reports
    ]


@app.get("/reports/{report_id}", response_model=schemas.ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = (
        db.query(models.Report)
        .filter(models.Report.id == report_id, models.Report.user_id == current_user.id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return _report_to_out(report)

@app.post("/reports/{report_id}/investment-plan")
def create_investment_plan(
    report_id: int,
    payload: schemas.InvestmentPlanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = (
        db.query(models.Report)
        .filter(models.Report.id == report_id, models.Report.user_id == current_user.id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    portfolio_result = json.loads(report.portfolio_result)
    plan = build_investment_plan(
        total_amount=payload.amount,
        asset_allocation=portfolio_result["asset_allocation"],
        recommended_stocks=portfolio_result["recommended_stocks"],
        category_guidance=portfolio_result.get("category_guidance"),
    )
    return plan


@app.get("/reports/{report_id}/historical-performance")
def get_historical_performance(
    report_id: int,
    period: str = "1y",
    amount: float = 10000.0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = (
        db.query(models.Report)
        .filter(models.Report.id == report_id, models.Report.user_id == current_user.id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    portfolio_result = json.loads(report.portfolio_result)
    return build_portfolio_history(
        asset_allocation=portfolio_result["asset_allocation"],
        recommended_stocks=portfolio_result["recommended_stocks"],
        period=period,
        invested_amount=amount,
    )

@app.get("/reports/{report_id}/investment-reasoning")
def get_investment_reasoning(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = (
        db.query(models.Report)
        .filter(models.Report.id == report_id, models.Report.user_id == current_user.id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    portfolio_result = json.loads(report.portfolio_result)
    return {
        "sectors": build_sector_reasoning(portfolio_result["recommended_sectors"]),
        "stocks": build_stock_reasoning(portfolio_result["recommended_stocks"]),
    }


def _report_to_out(report: models.Report) -> dict:
    return {
        "id": report.id,
        "created_at": report.created_at.replace(tzinfo=timezone.utc).isoformat(),
        "risk_level": report.risk_level,
        "confidence": report.confidence,
        "questionnaire_input": json.loads(report.questionnaire_input),
        "portfolio_result": json.loads(report.portfolio_result),
        "shap_result": json.loads(report.shap_result) if report.shap_result else None,
        "lime_result": json.loads(report.lime_result) if report.lime_result else None,
    }