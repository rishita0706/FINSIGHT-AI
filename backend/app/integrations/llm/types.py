from dataclasses import dataclass


@dataclass(frozen=True)
class Generation:
    text: str
    input_tokens: int
    output_tokens: int
