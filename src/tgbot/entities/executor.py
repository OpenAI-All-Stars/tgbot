from pydantic.dataclasses import dataclass


@dataclass
class ExecuteBashResponse:
    stdout: str
    stderr: str
