from pydantic.dataclasses import dataclass


@dataclass
class AddBalanceRequest:
    user_id: int
    microdollars: int
