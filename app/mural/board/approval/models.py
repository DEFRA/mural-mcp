import dataclasses
import datetime
import typing


@dataclasses.dataclass
class BoardApproval:
    board_id: str
    iao: str
    email: str
    submitted_at: datetime.datetime
    status: typing.Literal["pending", "approved", "rejected"] = "pending"

    @property
    def approved(self) -> bool:
        return self.status == "approved"
