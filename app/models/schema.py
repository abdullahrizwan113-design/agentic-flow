from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from datetime import datetime
import enum
from app.core.database import Base

class RunStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

VariantJSON = JSONB().with_variant(JSON(), 'sqlite')

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    title = Column(String)
    is_active = Column(Boolean, default=True)

class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"))
    definition = Column(VariantJSON)

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"))
    status = Column(Enum(RunStatus), default=RunStatus.PENDING)
    started_at = Column(DateTime, default=datetime.utcnow)

class RunLog(Base):
    __tablename__ = "run_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("workflow_runs.id"))
    node_id = Column(String)
    input_data = Column(VariantJSON)
    output_data = Column(VariantJSON)