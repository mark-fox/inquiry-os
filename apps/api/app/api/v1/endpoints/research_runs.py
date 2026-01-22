from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ResearchRun, ResearchRunStatus
from app.db.session import get_db
from app.schemas.research_runs import (
    ResearchRunCreate,
    ResearchRunRead,
    ResearchRunDetail,
)
from app.services.research_service import create_research_run_with_basic_plan

router = APIRouter(
    prefix="/research-runs",
    tags=["research-runs"],
)


@router.post(
    "",
    response_model=ResearchRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_run(
    payload: ResearchRunCreate,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunRead:
    """
    Create a new research run with an initial planner step.

    The planner is currently a simple rule-based function that generates
    generic sub-questions. Later this will be replaced with an LLM-backed
    planner agent and a more complete orchestration pipeline.
    """
    run = await create_research_run_with_basic_plan(
        payload=payload.model_dump(),
        db=db,
    )

    return run


@router.get(
    "/{run_id}",
    response_model=ResearchRunRead,
    status_code=status.HTTP_200_OK,
)
async def get_research_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunRead:
    """
    Fetch a single research run by its ID.

    For now this returns only the core run fields. In a later step we'll add
    a 'detail' schema that includes steps, sources, and answer.
    """
    result = await db.execute(
        select(ResearchRun).where(ResearchRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )

    return run


@router.get(
    "",
    response_model=list[ResearchRunRead],
    status_code=status.HTTP_200_OK,
)
async def list_research_runs(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[ResearchRunRead]:
    """
    List research runs, newest first.

    For now this is a simple cursor with limit/offset.
    We'll refine filtering and pagination later if needed.
    """
    stmt = (
        select(ResearchRun)
        .order_by(desc(ResearchRun.created_at))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    runs = result.scalars().all()

    return list(runs)


@router.get(
    "/{run_id}/detail",
    response_model=ResearchRunDetail,
    status_code=status.HTTP_200_OK,
)
async def get_research_run_detail(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunDetail:
    """
    Detailed view of a research run, including its steps and sources.

    For now this returns all steps and sources associated with the run.
    Later we will extend this with the final synthesized answer.
    """
    stmt = (
        select(ResearchRun)
        .options(
            selectinload(ResearchRun.steps),
            selectinload(ResearchRun.sources),
        )
        .where(ResearchRun.id == run_id)
    )

    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )

    return run
