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
    ResearchStepStatus,
    Source,
)
from datetime import datetime, timezone
from app.db.models import ResearchStepStatus

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
        Canonical detail loader: run + steps + sources + answer.
        """
        stmt = (
            select(ResearchRun)
            .options(
                selectinload(ResearchRun.steps),
                selectinload(ResearchRun.sources),
                selectinload(ResearchRun.answer),
            )
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

    async def _next_step_index(self, run_id: UUID) -> int:
        result = await self.db.execute(
            select(ResearchStep.step_index).where(ResearchStep.run_id == run_id)
        )
        indices = list(result.scalars().all())
        return (max(indices) + 1) if indices else 0
    
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

        next_index = await self._next_step_index(run_id)

        now = datetime.now(timezone.utc)

        search_step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.SEARCHER,
            status=ResearchStepStatus.COMPLETED,
            started_at=now,
            completed_at=now,
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

        has_reader = await self._has_step_type(run_id, ResearchStepType.READER)
        if not has_reader:
            raise InvalidPipelineStateError("Run reader before synthesis.")

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

        next_index = await self._next_step_index(run_id)

        now = datetime.now(timezone.utc)

        synth_step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.SYNTHESIZER,
            status=ResearchStepStatus.COMPLETED,
            started_at=now,
            completed_at=now,
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
    
    async def execute_dummy_pipeline(self, run_id: UUID) -> ResearchRun:
        run = await self.get_run_detail(run_id)

        if not await self._has_step_type(run_id, ResearchStepType.SEARCHER):
            await self.run_dummy_search(run_id)

        if not await self._has_step_type(run_id, ResearchStepType.READER):
            await self.run_dummy_reader(run_id)

        if not await self._has_step_type(run_id, ResearchStepType.SYNTHESIZER):
            await self.run_dummy_synthesis(run_id)

        return await self.get_run_detail(run_id)
    
    async def run_dummy_reader(self, run_id: UUID) -> ResearchRun:
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        already_read = await self._has_step_type(run_id, ResearchStepType.READER)
        if already_read:
            raise InvalidPipelineStateError("Reader has already been run for this research run.")

        has_search = await self._has_step_type(run_id, ResearchStepType.SEARCHER)
        if not has_search:
            raise InvalidPipelineStateError("Run search before reader.")

        result = await self.db.execute(select(Source).where(Source.run_id == run_id))
        sources = list(result.scalars().all())

        if not sources:
            raise InvalidPipelineStateError("No sources available to read.")

        now = datetime.now(timezone.utc)

        for src in sources:
            src.raw_content = (
                f"This is dummy fetched content for source: {src.title or src.url}. "
                f"It simulates the full text content retrieved from the web."
            )

            src.summary = (
                f"Summary for {src.title or src.url}. "
                f"This represents a condensed version of the source content."
            )

        next_index = await self._next_step_index(run_id)

        reader_step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.READER,
            status=ResearchStepStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            input={"source_ids": [str(s.id) for s in sources]},
            output={"source_count": len(sources)},
        )

        self.db.add(reader_step)

        await self.db.commit()
        await self.db.refresh(run)
        return run