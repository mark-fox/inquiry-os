from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ResearchRun,
    ResearchRunStatus,
    ResearchStep,
    ResearchStepType,
    Source,
)

# If your Answer model is available via app.db.models, we can eager load it too.
# If not, leave it out — the rest still works.
try:
    from app.db.models import Answer  # noqa: F401
    _HAS_ANSWER = True
except Exception:  # noqa: BLE001
    _HAS_ANSWER = False


class RunNotFoundError(Exception):
    pass


class InvalidPipelineStateError(Exception):
    pass


@dataclass(frozen=True)
class PipelineOrchestrator:
    """
    Central place for pipeline orchestration rules.

    Goal: keep route handlers thin and keep business rules testable and consistent.
    """

    db: AsyncSession

    async def get_run_detail(self, run_id: UUID) -> ResearchRun:
        """
        Canonical detail loader: run + steps + sources (+ answer if available).
        """
        options = [
            selectinload(ResearchRun.steps),
            selectinload(ResearchRun.sources),
        ]
        if _HAS_ANSWER:
            options.append(selectinload(ResearchRun.answer))

        stmt = (
            select(ResearchRun)
            .options(*options)
            .where(ResearchRun.id == run_id)
        )

        result = await self.db.execute(stmt)
        run = result.scalar_one_or_none()
        if run is None:
            raise RunNotFoundError("Research run not found")
        return run

    async def _has_step_type(self, run_id: UUID, step_type: ResearchStepType) -> bool:
        stmt = select(ResearchStep.id).where(
            ResearchStep.run_id == run_id,
            ResearchStep.step_type == step_type,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _set_status_running_if_pending(self, run: ResearchRun) -> None:
        if run.status == ResearchRunStatus.PENDING:
            run.status = ResearchRunStatus.RUNNING

    async def _set_status_completed(self, run: ResearchRun) -> None:
        run.status = ResearchRunStatus.COMPLETED

    async def run_dummy_search(self, run_id: UUID) -> ResearchRun:
        """
        Orchestrated dummy search:
        - validates pipeline state
        - appends search step + sources (via existing behavior)
        - transitions status to RUNNING
        """
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        # Rule: don't run search twice (keeps UI and pipeline clean)
        already_searched = await self._has_step_type(run_id, ResearchStepType.SEARCHER)
        if already_searched:
            raise InvalidPipelineStateError("Search has already been run for this research run.")

        # Rule: planner should exist first (it should, but enforce)
        has_planner = await self._has_step_type(run_id, ResearchStepType.PLANNER)
        if not has_planner:
            raise InvalidPipelineStateError("Planner step missing; cannot run search.")

        # --- Existing dummy behavior (inline, intentionally small) ---
        query = run.query

        search_step = ResearchStep(
            run_id=run.id,
            step_index=1,
            step_type=ResearchStepType.SEARCHER,
            input={"query": query},
            output={
                "notes": "Dummy searcher v0 – no real web search performed.",
                "hint": "Later this will hit a search API and populate real sources.",
            },
        )
        self.db.add(search_step)

        base_slug = query.lower().replace(" ", "-")[:50] or "research-topic"
        sources = [
            Source(
                run_id=run.id,
                url=f"https://example.com/articles/{base_slug}-overview",
                title="High-level overview related to your research question",
                raw_content=None,
                summary="Overview article (dummy source for dev/testing).",
                relevance_score=0.9,
                extra_metadata={"source_type": "overview", "dummy": True},
            ),
            Source(
                run_id=run.id,
                url=f"https://example.com/blog/{base_slug}-tradeoffs",
                title="Discussion of tradeoffs and practical considerations",
                raw_content=None,
                summary="Tradeoffs and pros/cons (dummy source for dev/testing).",
                relevance_score=0.8,
                extra_metadata={"source_type": "discussion", "dummy": True},
            ),
            Source(
                run_id=run.id,
                url=f"https://example.com/docs/{base_slug}-reference",
                title="Reference documentation or spec-style material",
                raw_content=None,
                summary="Reference-style material (dummy source for dev/testing).",
                relevance_score=0.75,
                extra_metadata={"source_type": "reference", "dummy": True},
            ),
        ]
        self.db.add_all(sources)
        # --- end existing dummy behavior ---

        await self._set_status_running_if_pending(run)

        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def run_dummy_synthesis(self, run_id: UUID) -> ResearchRun:
        """
        Orchestrated dummy synthesis:
        - requires search to have run
        - prevents duplicate synthesis
        - transitions status to COMPLETED
        """
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        already_synthesized = await self._has_step_type(run_id, ResearchStepType.SYNTHESIZER)
        if already_synthesized:
            raise InvalidPipelineStateError("Synthesis has already been run for this research run.")

        has_search = await self._has_step_type(run_id, ResearchStepType.SEARCHER)
        if not has_search:
            raise InvalidPipelineStateError("Run search before synthesis.")

        # Load sources
        result = await self.db.execute(select(Source).where(Source.run_id == run_id))
        sources = list(result.scalars().all())

        if not sources:
            answer_text = (
                "No sources are currently attached to this research run. "
                "Run the searcher agent first to collect relevant sources."
            )
        else:
            lines: list[str] = []
            lines.append("This is a dummy synthesized answer based on the attached sources.")
            lines.append("")
            lines.append(f"Research question: {run.query}")
            lines.append("")
            lines.append("The system considered the following sources:")
            for idx, src in enumerate(sources, start=1):
                title = src.title or src.url
                lines.append(f"{idx}. {title} — {src.url}")
            lines.append("")
            lines.append(
                "A proper LLM-backed synthesizer will later read and compare these "
                "sources in detail to produce a nuanced, citation-rich answer."
            )
            answer_text = "\n".join(lines)

        # Compute next step_index safely (no assumptions)
        result = await self.db.execute(
            select(ResearchStep.step_index).where(ResearchStep.run_id == run_id)
        )
        indices = list(result.scalars().all())
        next_index = (max(indices) + 1) if indices else 0

        synth_step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.SYNTHESIZER,
            input={"source_ids": [str(s.id) for s in sources]},
            output={
                "answer": answer_text,
                "notes": "Dummy synthesizer v0 – no real LLM call performed.",
                "source_count": len(sources),
            },
        )
        self.db.add(synth_step)

        await self._set_status_completed(run)

        await self.db.commit()
        await self.db.refresh(run)
        return run