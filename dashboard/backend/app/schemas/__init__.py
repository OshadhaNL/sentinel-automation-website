from typing import Literal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginInput(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value


class TesterInput(LoginInput):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=1024)

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError('Name must contain at least two characters.')
        return value.strip()


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope_type: Literal['all', 'module', 'test']
    scope_value: str | None = None
    selection: Literal['all', 'positive', 'negative'] = 'all'
    browser_mode: Literal['headed', 'headless'] = 'headless'
    camera_mode: Literal['exclude', 'include', 'only'] = 'exclude'
    workers: int = Field(default=1, ge=1, le=32, strict=True)
