# File state enums
# Processing result objects
# No logic

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessResult:
    success: bool
    error: Optional[str] = None
    stage: Optional[str] = None