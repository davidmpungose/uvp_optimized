from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ApiSettings:
    host: str
    port: int
    allowed_origins: tuple[str, ...]
    default_page_size: int
    maximum_page_size: int
    maximum_selected_quarters: int

    @classmethod
    def from_environment(cls) -> "ApiSettings":
        origins = tuple(
            item.strip()
            for item in os.getenv(
                "API_ALLOWED_ORIGINS",
                "http://localhost:8000,http://127.0.0.1:8000",
            ).split(",")
            if item.strip()
        )
        settings = cls(
            host=os.getenv("API_HOST", "127.0.0.1").strip(),
            port=int(os.getenv("API_PORT", "8080")),
            allowed_origins=origins,
            default_page_size=int(os.getenv("API_DEFAULT_PAGE_SIZE", "25")),
            maximum_page_size=int(os.getenv("API_MAXIMUM_PAGE_SIZE", "200")),
            maximum_selected_quarters=int(
                os.getenv("API_MAXIMUM_SELECTED_QUARTERS", "40")
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.host:
            raise ValueError("API_HOST cannot be empty.")
        if not 1 <= self.port <= 65535:
            raise ValueError("API_PORT must be between 1 and 65535.")
        if self.default_page_size < 1:
            raise ValueError("API_DEFAULT_PAGE_SIZE must be positive.")
        if self.maximum_page_size < self.default_page_size:
            raise ValueError(
                "API_MAXIMUM_PAGE_SIZE cannot be smaller than the default."
            )
        if self.maximum_selected_quarters < 1:
            raise ValueError("API_MAXIMUM_SELECTED_QUARTERS must be positive.")
