from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResearchRun, ResearchRunStatus
from app.db.session import get_db, AsyncSessionLocal
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
from app.schemas.research_state import ResearchRunState
from app.schemas.execution import ExecutionMode
from app.core.config import get_settings
from app.schemas.execution_response import ExecutionAccepted

router = APIRouter(
    prefix="/research-runs",
    tags=["research-runs"],
)

async def _execute_pipeline_in_background(run_id: UUID, mode: ExecutionMode) -> None:
    async with AsyncSessionLocal() as db:
        orchestrator = PipelineOrchestrator(db=db)
        try:
            await orchestrator.execute(run_id, mode)
        except Exception:
            # The orchestrator already records failure state/events.
            # Swallow here so Starlette background tasks do not dump a giant traceback.
            return


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
    "/{run_id}/execute-dummy",
    response_model=ResearchRunDetail,
    status_code=status.HTTP_200_OK,
)
async def execute_dummy_pipeline(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunDetail:
    orchestrator = PipelineOrchestrator(db=db)

    try:
        run = await orchestrator.execute_dummy_pipeline(run_id)
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
    "/{run_id}/search",
    response_model=ResearchRunDetail,
    status_code=status.HTTP_200_OK,
)
async def run_web_search(
    run_id: UUID,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunDetail:
    orchestrator = PipelineOrchestrator(db=db)

    try:
        await orchestrator.run_web_search(run_id, limit=limit)
        run = await orchestrator.get_run_detail(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail="Research run not found")
    except InvalidPipelineStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Search provider failed")

    return run


@router.post(
    "/{run_id}/read",
    response_model=ResearchRunDetail,
    status_code=status.HTTP_200_OK,
)
async def run_web_reader(
    run_id: UUID,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunDetail:
    orchestrator = PipelineOrchestrator(db=db)

    try:
        await orchestrator.run_web_reader(run_id, limit=limit)
        run = await orchestrator.get_run_detail(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail="Research run not found")
    except InvalidPipelineStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Reader failed")

    return run


@router.get(
    "/{run_id}/state",
    response_model=ResearchRunState,
    status_code=status.HTTP_200_OK,
)
async def get_research_run_state(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchRunState:
    orchestrator = PipelineOrchestrator(db=db)

    try:
        payload = await orchestrator.get_run_state(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail="Research run not found")

    return payload


@router.post(
    "/{run_id}/execute",
    response_model=ExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_pipeline(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    mode: ExecutionMode = ExecutionMode.REAL,
    db: AsyncSession = Depends(get_db),
) -> ExecutionAccepted:
    settings = get_settings()

    if mode == ExecutionMode.DUMMY and settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dummy mode is disabled in production.",
        )

    run = await db.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )

    if run.status == ResearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Research run is already running.",
        )

    run.status = ResearchRunStatus.RUNNING
    run.error_message = None
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(_execute_pipeline_in_background, run_id, mode)

    return ExecutionAccepted(
        run_id=run.id,
        status=run.status,
        message="Pipeline execution started.",
    )