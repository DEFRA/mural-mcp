import datetime
import enum

import pydantic
from pydantic.alias_generators import to_camel


class AccessRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BoardAccessRequest(pydantic.BaseModel):
    """A request for governed access to a Mural board: request -> IAO review
    -> decision. Backs BoardGuard (see guard.py) — once approved, an agent's
    existing get_board_summary/get_region/etc. calls for that board simply
    start succeeding; there is nothing further for a tool to do.
    """

    model_config = pydantic.ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    user_id: str
    board_id: str
    reason: str
    iao: str  # nominated information-asset owner, named at request time
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    reviewer_id: str | None = None
    decision_reason: str | None = None
    data_handling_form_ref: str | None = None
    risk_assessment_ref: str | None = None
    created_at: datetime.datetime
    decided_at: datetime.datetime | None = None

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def approved(self) -> bool:
        return self.status == AccessRequestStatus.APPROVED
