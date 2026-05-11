"""Mendelian randomization agent for causal target validation."""

from __future__ import annotations

import math
from statistics import median

from pydantic import BaseModel, Field

from trident.agents.base import ProvenanceResult, confidence_band
from trident.agents.hypothesis_fixtures import mr_fixture_data
from trident.agents.tooling import LocalToolNode, ToolDefinition, build_tool_node


class GeneticInstrument(BaseModel):
    variant: str
    beta_exposure: float
    beta_outcome: float
    se_outcome: float = Field(gt=0.0)


class MRQuery(BaseModel):
    exposure: str
    outcome: str
    use_rpy2: bool = False


class MREstimate(BaseModel):
    method: str
    beta: float
    standard_error: float
    p_value: float


class MRSensitivity(BaseModel):
    cochran_q: float
    i2: float = Field(ge=0.0, le=1.0)
    egger_intercept: float
    egger_intercept_p: float
    steiger_correct_direction: bool
    coloc_h4: float = Field(ge=0.0, le=1.0)


class MRResult(ProvenanceResult):
    exposure: str
    outcome: str
    instruments: list[GeneticInstrument]
    estimates: list[MREstimate]
    posterior_causal_probability: float = Field(ge=0.0, le=1.0)
    direction: str
    significant: bool
    sensitivity: MRSensitivity


class MRAgent:
    """Two-sample Mendelian Randomization for causal target validation.

    Uses a pure-Python IVW/Egger/weighted-median baseline by default. The public
    method shape leaves room for an rpy2 TwoSampleMR bridge while keeping tests
    deterministic and portable.
    """

    name = "mendelian_randomization"

    def __init__(self) -> None:
        self.fixtures = mr_fixture_data()
        self.tools = [
            ToolDefinition(
                "load_instruments", "Load cis instruments and outcome stats", self.load_instruments
            ),
            ToolDefinition("estimate_mr", "Run IVW/Egger/median MR", self.estimate),
        ]
        self.tool_node = build_tool_node(self.tools)
        self.local_tool_node = (
            self.tool_node
            if isinstance(self.tool_node, LocalToolNode)
            else LocalToolNode(self.tools)
        )

    def load_instruments(self, exposure: str, outcome: str) -> dict:
        key = self._key(exposure, outcome)
        if key not in self.fixtures:
            return {
                "exposure": exposure,
                "outcome": outcome,
                "coloc_h4": 0.05,
                "steiger_correct_direction": False,
                "instruments": [],
                "source_urls": ["https://www.ebi.ac.uk/gwas/"],
            }
        return self.fixtures[key]

    def estimate(self, instruments: list[GeneticInstrument]) -> list[MREstimate]:
        if not instruments:
            return [
                MREstimate(method="IVW", beta=0.0, standard_error=1.0, p_value=1.0),
                MREstimate(method="MR-Egger", beta=0.0, standard_error=1.0, p_value=1.0),
                MREstimate(method="weighted_median", beta=0.0, standard_error=1.0, p_value=1.0),
            ]

        ivw_beta, ivw_se = self._ivw(instruments)
        egger_intercept, egger_beta, egger_se = self._egger(instruments)
        ratios = [instrument.beta_outcome / instrument.beta_exposure for instrument in instruments]
        weights = [
            instrument.beta_exposure**2 / instrument.se_outcome**2 for instrument in instruments
        ]
        median_beta = self._weighted_median(ratios, weights)
        median_se = max(ivw_se * 1.25, 1e-6)
        return [
            MREstimate(
                method="IVW",
                beta=ivw_beta,
                standard_error=ivw_se,
                p_value=self._two_sided_p(ivw_beta, ivw_se),
            ),
            MREstimate(
                method="MR-Egger",
                beta=egger_beta,
                standard_error=egger_se,
                p_value=self._two_sided_p(egger_beta, egger_se),
            ),
            MREstimate(
                method="weighted_median",
                beta=median_beta,
                standard_error=median_se,
                p_value=self._two_sided_p(median_beta, median_se),
            ),
        ]

    def run(self, query: MRQuery) -> MRResult:
        payload = self.local_tool_node.call_tool(
            "load_instruments", exposure=query.exposure, outcome=query.outcome
        )
        instruments = [GeneticInstrument(**row) for row in payload["instruments"]]
        estimates = self.local_tool_node.call_tool("estimate_mr", instruments=instruments)
        sensitivity = self._sensitivity(
            instruments,
            ivw_estimate=next(estimate for estimate in estimates if estimate.method == "IVW"),
            coloc_h4=payload["coloc_h4"],
            steiger_correct_direction=payload["steiger_correct_direction"],
        )
        posterior = self._posterior(estimates, sensitivity)
        ivw = next(estimate for estimate in estimates if estimate.method == "IVW")
        return MRResult(
            exposure=query.exposure,
            outcome=query.outcome,
            instruments=instruments,
            estimates=estimates,
            posterior_causal_probability=posterior,
            direction="protective"
            if ivw.beta < 0
            else "risk_increasing"
            if ivw.beta > 0
            else "null",
            significant=ivw.p_value < 0.001 and sensitivity.coloc_h4 > 0.8,
            sensitivity=sensitivity,
            source_urls=payload["source_urls"],
            confidence_band=confidence_band(posterior),
            agent_name=self.name,
            tool_calls=list(self.local_tool_node.calls),
        )

    @staticmethod
    def _key(exposure: str, outcome: str) -> tuple[str, str]:
        exposure_key = exposure.strip().lower()
        if exposure_key == "pcsk9":
            exposure_key = "PCSK9"
        outcome_key = outcome.strip().lower()
        if "ldl" in outcome_key:
            outcome_key = "LDL cholesterol"
        elif "diabetes" in outcome_key:
            outcome_key = "type 2 diabetes"
        return exposure_key, outcome_key

    @staticmethod
    def _ivw(instruments: list[GeneticInstrument]) -> tuple[float, float]:
        numerator = sum(
            instrument.beta_exposure * instrument.beta_outcome / instrument.se_outcome**2
            for instrument in instruments
        )
        denominator = sum(
            instrument.beta_exposure**2 / instrument.se_outcome**2 for instrument in instruments
        )
        beta = numerator / denominator
        se = math.sqrt(1 / denominator)
        return beta, se

    @staticmethod
    def _egger(instruments: list[GeneticInstrument]) -> tuple[float, float, float]:
        weights = [1 / instrument.se_outcome**2 for instrument in instruments]
        sx = sum(
            weight * instrument.beta_exposure for weight, instrument in zip(weights, instruments)
        )
        sy = sum(
            weight * instrument.beta_outcome for weight, instrument in zip(weights, instruments)
        )
        sw = sum(weights)
        x_bar = sx / sw
        y_bar = sy / sw
        sxx = sum(
            weight * (instrument.beta_exposure - x_bar) ** 2
            for weight, instrument in zip(weights, instruments)
        )
        sxy = sum(
            weight * (instrument.beta_exposure - x_bar) * (instrument.beta_outcome - y_bar)
            for weight, instrument in zip(weights, instruments)
        )
        beta = sxy / max(sxx, 1e-12)
        intercept = y_bar - beta * x_bar
        se = math.sqrt(1 / max(sxx, 1e-12))
        return intercept, beta, se

    @staticmethod
    def _weighted_median(values: list[float], weights: list[float]) -> float:
        ordered = sorted(zip(values, weights), key=lambda item: item[0])
        half = sum(weights) / 2
        running = 0.0
        for value, weight in ordered:
            running += weight
            if running >= half:
                return value
        return median(values)

    @staticmethod
    def _two_sided_p(beta: float, standard_error: float) -> float:
        z = abs(beta / max(standard_error, 1e-12))
        return math.erfc(z / math.sqrt(2))

    @staticmethod
    def _sensitivity(
        instruments: list[GeneticInstrument],
        ivw_estimate: MREstimate,
        coloc_h4: float,
        steiger_correct_direction: bool,
    ) -> MRSensitivity:
        if not instruments:
            return MRSensitivity(
                cochran_q=0.0,
                i2=0.0,
                egger_intercept=0.0,
                egger_intercept_p=1.0,
                steiger_correct_direction=False,
                coloc_h4=coloc_h4,
            )
        ratios = [instrument.beta_outcome / instrument.beta_exposure for instrument in instruments]
        weights = [
            instrument.beta_exposure**2 / instrument.se_outcome**2 for instrument in instruments
        ]
        q = sum(weight * (ratio - ivw_estimate.beta) ** 2 for ratio, weight in zip(ratios, weights))
        i2 = max(0.0, min(1.0, (q - (len(instruments) - 1)) / max(q, 1e-9)))
        intercept, _, intercept_se = MRAgent._egger(instruments)
        return MRSensitivity(
            cochran_q=q,
            i2=i2,
            egger_intercept=intercept,
            egger_intercept_p=MRAgent._two_sided_p(intercept, intercept_se),
            steiger_correct_direction=steiger_correct_direction,
            coloc_h4=coloc_h4,
        )

    @staticmethod
    def _posterior(estimates: list[MREstimate], sensitivity: MRSensitivity) -> float:
        ivw = next(estimate for estimate in estimates if estimate.method == "IVW")
        median_estimate = next(
            estimate for estimate in estimates if estimate.method == "weighted_median"
        )
        evidence_lr = 1.0
        if ivw.p_value < 0.001:
            evidence_lr *= 10
        elif ivw.p_value < 0.05:
            evidence_lr *= 3
        if ivw.p_value < 0.05 and math.copysign(1, ivw.beta or 1) == math.copysign(
            1, median_estimate.beta or 1
        ):
            evidence_lr *= 2
        if sensitivity.coloc_h4 > 0.8:
            evidence_lr *= 8
        elif sensitivity.coloc_h4 > 0.5:
            evidence_lr *= 3
        if sensitivity.steiger_correct_direction:
            evidence_lr *= 2
        else:
            evidence_lr *= 0.5
        if sensitivity.coloc_h4 < 0.2:
            evidence_lr *= 0.25
        if sensitivity.i2 > 0.5 or sensitivity.egger_intercept_p < 0.05:
            evidence_lr *= 0.35
        return evidence_lr / (1 + evidence_lr)


MendelianRandomizationAgent = MRAgent
