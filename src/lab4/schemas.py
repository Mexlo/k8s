"""Схеми запитів із валідацією вхідних даних регулярними виразами."""

from pydantic import BaseModel, Field

# Назва: літери (будь-яка мова), цифри, пробіл, крапка, дефіс, підкреслення; 2-100 символів
NAME_PATTERN = r"^[\w][\w .\-]{1,99}$"
# Ідеологія: те саме, але дозволені також «/» і «,» (напр. «Політична / державна»)
IDEOLOGY_PATTERN = r"^[\w][\w .,/\-]{1,99}$"
# Дата у форматі РРРР-ММ-ДД
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class GroupIn(BaseModel):
    """Тіло запитів POST та PUT."""

    name: str = Field(pattern=NAME_PATTERN)
    founded: int = Field(ge=1970, le=2026)
    ideology: str = Field(pattern=IDEOLOGY_PATTERN)
    active: bool = False
    last_action: str | None = Field(default=None, pattern=DATE_PATTERN)
