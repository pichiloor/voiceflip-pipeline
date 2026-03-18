from typing import Literal
from pydantic import BaseModel

ScenarioType = Literal["ok", "timeout", "transient_fail_then_ok", "hard_fail"]


class RequestPayload(BaseModel):
    input: str
    scenario: ScenarioType = "ok"
    optional_scenario: ScenarioType = "ok"
