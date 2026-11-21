import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, utcnow


def new_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True))


class TestCase(Base):
    __tablename__ = 'test_cases'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(Text)
    module: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(20), default='Unclassified')
    pytest_node_id: Mapped[str] = mapped_column(Text, unique=True)
    requires_real_camera: Mapped[bool] = mapped_column(Boolean, default=False)
    camera_classified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)


class TestRun(Base):
    __tablename__ = 'test_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    executed_by_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    scope_type: Mapped[str] = mapped_column(String(20))
    scope_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selection: Mapped[str] = mapped_column(String(20))
    browser_mode: Mapped[str] = mapped_column(String(20))
    camera_mode: Mapped[str] = mapped_column(String(20))
    workers: Mapped[int] = mapped_column(Integer, default=1, server_default='1')
    status: Mapped[str] = mapped_column(String(25), index=True, default='Pending')
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    html_report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)


class TestResult(Base):
    __tablename__ = 'test_results'
    __table_args__ = (
        UniqueConstraint('test_run_id', 'test_case_id'),
        Index('ix_results_case_time', 'test_case_id', 'executed_at'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_run_id: Mapped[str] = mapped_column(ForeignKey('test_runs.id'), index=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey('test_cases.id'))
    # Pending is an internal placeholder, excluded from execution counts.
    status: Mapped[str] = mapped_column(String(20), default='Pending')
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunnerLock(Base):
    __tablename__ = 'runner_lock'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str | None] = mapped_column(String(36), nullable=True)


class DiscoveryInfo(Base):
    __tablename__ = 'discovery_info'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discovered_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    count: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
