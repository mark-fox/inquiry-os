from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ResearchRun, ResearchRunStatus
from app.db.session import get_db
from app.schemas.research_runs import ResearchRunCreate, ResearchRunRead

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
    Create a new research run in 'pending' status.

    For now this only persists the run; the agent orchestration pipeline
    will be triggered in a later step.
    """
    settings = get_settings()

    run = ResearchRun(
        query=payload.query,
        title=payload.title,
        status=ResearchRunStatus.PENDING,
        model_provider=f"{settings.llm_provider}:{settings.llm_model}",
    )

    db.add(run)
    await db.commit()
    await db.refresh(run)

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
