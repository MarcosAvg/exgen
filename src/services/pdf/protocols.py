from typing import Callable, Optional, Protocol

from src.domain.models import EvidenciaData

ProgressCallback = Optional[Callable[[float, str], None]]


class EvidenceReportGenerator(Protocol):
    def generate(
        self,
        data: EvidenciaData,
        output_path: str,
        progress_callback: ProgressCallback = None,
    ) -> str: ...
