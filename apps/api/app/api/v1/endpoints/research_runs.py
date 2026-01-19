from fastapi import APIRouter, Depends, status
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
