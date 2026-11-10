"""prompts/*.txt를 읽어 항목 목록을 구성함. 파일 1개 = 항목 1개."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER = "{conversation}"
DEFAULT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class PromptItem:
    item: str  # 파일명(확장자 제외), 예: CBT_1_guided_discovery
    template: str
    sha256: str

    def render(self, conversation_text: str) -> str:
        # str.format은 프롬프트의 다른 중괄호와 충돌하므로 replace 사용
        return self.template.replace(PLACEHOLDER, conversation_text)


def load_prompts(directory: Path | str = DEFAULT_DIR, only: list[str] | None = None) -> list[PromptItem]:
    directory = Path(directory)
    items = []
    for path in sorted(directory.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER not in text:
            raise ValueError(f"{path.name}: {PLACEHOLDER} 자리표시자가 없음")
        items.append(PromptItem(path.stem, text, hashlib.sha256(text.encode("utf-8")).hexdigest()))
    if only:
        missing = set(only) - {i.item for i in items}
        if missing:
            raise ValueError(f"존재하지 않는 항목: {sorted(missing)}")
        items = [i for i in items if i.item in only]
    if not items:
        raise ValueError(f"{directory}에 프롬프트가 없음")
    return items
