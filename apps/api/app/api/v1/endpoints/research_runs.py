from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResearchRun
from app.db.session import get_db
from app.schemas.research_runs import (
    ResearchRunCreate,
    ResearchRunRead,
    ResearchRunDetail,
)
from app.services.research_service import (
    create_research_run_with_basic_plan,
)

from app.services.pipeline_orchestrator import (
    PipelineOrchestrator,
    RunNotFoundError,
    InvalidPipelineStateError,
)

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
    orchestrator = PipelineOrchestrator(db=db)

    try:
        run = await orchestrator.get_run_detail(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )

    return run


@router.post(
    "/{run_id}/search-dummy",
    response_model=ResearchRunDetail,
    status_code=status.HTTP_200_OK,
)
async def run_dummy_search(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunDetail:
    orchestrator = PipelineOrchestrator(db=db)

    try:
        await orchestrator.run_dummy_search(run_id)
        run = await orchestrator.get_run_detail(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )
    except InvalidPipelineStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return run


@router.post(
    "/{run_id}/synthesize-dummy",
    response_model=ResearchRunDetail,
    status_code=status.HTTP_200_OK,
)
async def run_dummy_synthesis(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunDetail:
    orchestrator = PipelineOrchestrator(db=db)

    try:
        await orchestrator.run_dummy_synthesis(run_id)
        run = await orchestrator.get_run_detail(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )
    except InvalidPipelineStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return run