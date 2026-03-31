from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SecDetail(BaseModel):
    model_config = {"populate_by_name": True}

    requested: Optional[str] = None
    classification: Optional[str] = None
    symbol: Optional[str] = None
    cusip: Optional[str] = Field(default=None, alias="CUSIP")


class EarningsQuarter(BaseModel):
    model_config = {"populate_by_name": True}

    fiscal_qtr: int = Field(alias="fiscalQtr")
    fiscal_yr: int = Field(alias="fiscalYr")
    report_date: Optional[str] = Field(default=None, alias="reportDate")
    adjusted_eps: Optional[float] = Field(default=None, alias="adjustedEPS")
    consensus_est: Optional[float] = Field(default=None, alias="consensusEst")


class EarningsDetail(BaseModel):
    model_config = {"populate_by_name": True}

    sec_detail: Optional[SecDetail] = Field(default=None, alias="secDetail")
    quarters: list[EarningsQuarter] = Field(default_factory=list)
    eps_prev_qtr_vs_prev_yr_qtr: Optional[float] = Field(
        default=None, alias="epsPrevQtrVsPrevYrQtr"
    )

    @classmethod
    def from_api_dict(cls, data: dict) -> "EarningsDetail":
        sec_detail = SecDetail.model_validate(data.get("secDetail") or {})
        qtr_hist = (data.get("qtrHistDetails") or {}).get("qtrHistDetail") or []
        quarters = [EarningsQuarter.model_validate(q) for q in qtr_hist]
        return cls(
            sec_detail=sec_detail,
            quarters=quarters,
            eps_prev_qtr_vs_prev_yr_qtr=data.get("epsPrevQtrVsPrevYrQtr"),
        )


class EarningsResponse(BaseModel):
    earnings: list[EarningsDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "EarningsResponse":
        detail_list = (
            (data.get("earning") or {})
            .get("earningDetails", {})
            .get("earningDetail", [])
        ) or []
        return cls(
            earnings=[EarningsDetail.from_api_dict(d) for d in detail_list]
        )


class DividendHistory(BaseModel):
    model_config = {"populate_by_name": True}

    amt: Optional[float] = None
    announce_date: Optional[str] = Field(default=None, alias="announceDate")
    freq_name: Optional[str] = Field(default=None, alias="freqName")
    pay_date: Optional[str] = Field(default=None, alias="payDate")
    ex_date: Optional[str] = Field(default=None, alias="exDate")
    record_date: Optional[str] = Field(default=None, alias="recordDate")
    currency: Optional[str] = None
    type: Optional[str] = None
    ex_date_cal_qtr: Optional[str] = Field(default=None, alias="exDateCalQtr")
    ex_date_cal_yr: Optional[int] = Field(default=None, alias="exDateCalYr")


class DividendDetail(BaseModel):
    model_config = {"populate_by_name": True}

    sec_detail: Optional[SecDetail] = Field(default=None, alias="secDetail")
    amt: Optional[float] = None
    announce_date: Optional[str] = None
    ex_div_date: Optional[str] = None
    yld_ttm: Optional[float] = None
    indicated_ann_div: Optional[float] = None
    history: list[DividendHistory] = Field(default_factory=list)

    @classmethod
    def from_api_dict(cls, data: dict) -> "DividendDetail":
        sec_detail = SecDetail.model_validate(data.get("secDetail") or {})
        equity = data.get("equityDetail") or {}
        hist_list = (equity.get("divHistDetails") or {}).get("divHistDetail") or []
        history = [DividendHistory.model_validate(h) for h in hist_list]
        return cls(
            sec_detail=sec_detail,
            amt=equity.get("amt"),
            announce_date=equity.get("announceDate"),
            ex_div_date=equity.get("exDivDate"),
            yld_ttm=equity.get("yldTTM"),
            indicated_ann_div=equity.get("indicatedAnnDiv"),
            history=history,
        )


class DividendsResponse(BaseModel):
    dividends: list[DividendDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "DividendsResponse":
        detail_list = (
            (data.get("dividend") or {})
            .get("dividendDetails", {})
            .get("dividendDetail", [])
        ) or []
        return cls(
            dividends=[DividendDetail.from_api_dict(d) for d in detail_list]
        )
