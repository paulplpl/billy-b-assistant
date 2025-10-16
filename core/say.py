from typing import Literal, Optional


def _classify_kind(text: str) -> tuple[Literal["prompt", "literal", "raw"], str]:
    s = text.strip()
    if s.startswith("{{") and s.endswith("}}"):
        return "prompt", s[2:-2].strip()
    return "literal", s


async def say(text: str, *, interactive: Optional[bool] = None):
    # 🔁 Lazy import to avoid: session -> mqtt -> say -> session
    from .session import BillySession

    kind, cleaned = _classify_kind(text)

    session = BillySession(
        kickoff_text=cleaned,
        kickoff_kind=kind,
        kickoff_to_interactive=(interactive is True),
        autofollowup=(
            "always"
            if interactive is True
            else "never"
            if interactive is False
            else "auto"
        ),
    )

    if interactive is False:
        session.run_mode = "dory"  # one-and-done

    await session.start()
