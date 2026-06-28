from fastapi import APIRouter

from backend.models.signal_engine import create_sample_signal_cards

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "retailsignal-os"}


@router.get("/signals/live")
def live_signals() -> list[dict]:
    return [card.model_dump(mode="json") for card in create_sample_signal_cards()]
