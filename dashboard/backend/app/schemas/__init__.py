from typing import Literal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmailInput(BaseModel):
    email: str = Field(max_length=254)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value


class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=1024)


class InviteInput(EmailInput):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=2, max_length=100)

    @field_validator('email')
    @classmethod
    def require_company_email(cls, value):
        if value.split('@')[-1] != 'northlark.com':
            raise ValueError('Only @northlark.com email addresses are allowed.')
        return value

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError('Name must contain at least two characters.')
        return value.strip()


class TesterInput(InviteInput):
    password: str = Field(min_length=6, max_length=128)


class OutlookTesterInput(InviteInput):
    designation: str = Field(min_length=2, max_length=100)

    @field_validator('designation')
    @classmethod
    def normalize_designation(cls, value):
        if len(value.strip()) < 2:
            raise ValueError('Designation must contain at least two characters.')
        return value.strip()


class AcceptInvitationInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=6, max_length=128)


class PasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    password: str = Field(min_length=6, max_length=128)


class AccountStatusInput(BaseModel):
    is_active: bool = Field(strict=True)


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope_type: Literal['all', 'module', 'test']
    scope_value: str | None = None
    selection: Literal['all', 'positive', 'negative'] = 'all'
    browser_mode: Literal['headed', 'headless'] = 'headless'
    camera_mode: Literal['exclude', 'include', 'only'] = 'exclude'
    workers: int = Field(default=1, ge=1, le=32, strict=True)
    browsers: list[Literal['chromium', 'chrome', 'edge', 'webkit']] = Field(
        default_factory=lambda: ['chromium'], min_length=1, max_length=4)

    @field_validator('browsers')
    @classmethod
    def unique_browsers(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('Select each browser only once.')
        return value
