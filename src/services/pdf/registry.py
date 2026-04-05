from collections.abc import Callable

from src.services.pdf.protocols import EvidenceReportGenerator

DEFAULT_EVIDENCE_BACKEND_ID = "reportlab_letter"

_factories: dict[str, Callable[[], EvidenceReportGenerator]] = {}


def register_evidence_backend(
    backend_id: str,
    factory: Callable[[], EvidenceReportGenerator],
) -> None:
    _factories[backend_id] = factory


def get_evidence_generator(backend_id: str | None = None) -> EvidenceReportGenerator:
    bid = backend_id or DEFAULT_EVIDENCE_BACKEND_ID
    if bid not in _factories:
        raise KeyError(f"Backend de informe desconocido: {bid!r}")
    return _factories[bid]()


def list_evidence_backend_ids() -> tuple[str, ...]:
    return tuple(sorted(_factories.keys()))


def _register_builtin_backends() -> None:
    from src.services.pdf.reportlab_generator import ReportlabLetterEvidenciaGenerator

    register_evidence_backend(
        DEFAULT_EVIDENCE_BACKEND_ID,
        lambda: ReportlabLetterEvidenciaGenerator(),
    )


_register_builtin_backends()
