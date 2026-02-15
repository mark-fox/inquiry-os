from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
import json

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
    PipelineEvent,
    PipelineEventType,
    ExecutionMode as DbExecutionMode,
)
from datetime import datetime, timezone
from app.services.search_clients.duckduckgo_client import DuckDuckGoClient
from app.services.web_fetcher import fetch_html, extract_text_from_html, basic_summary, UnsafeUrlError
from app.schemas.execution import ExecutionMode
from app.core.llm import LLMClient, get_llm_client
from app.schemas.synthesis import SynthesisOutput

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
                selectinload(ResearchRun.events),
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

                summ = (src.summary or "").strip()
                if summ:
                    lines.append(f"   Summary: {summ}")
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
    
    async def execute_pipeline(self, run_id: UUID) -> ResearchRun:
        # Always return the latest persisted state at the end
        await self.get_run_detail(run_id)

        if not await self._has_step_type(run_id, ResearchStepType.SEARCHER):
            await self.run_web_search(run_id, limit=5)

        if not await self._has_step_type(run_id, ResearchStepType.READER):
            await self.run_web_reader(run_id, limit=5)

        if not await self._has_step_type(run_id, ResearchStepType.SYNTHESIZER):
            await self.run_llm_synthesis(run_id)

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
    
    async def run_web_search(self, run_id: UUID, limit: int = 5) -> ResearchRun:
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        already_searched = await self._has_step_type(run_id, ResearchStepType.SEARCHER)
        if already_searched:
            raise InvalidPipelineStateError("Search has already been run for this research run.")

        has_planner = await self._has_step_type(run_id, ResearchStepType.PLANNER)
        if not has_planner:
            raise InvalidPipelineStateError("Planner step missing; cannot run search.")

        client = DuckDuckGoClient()
        results = await client.search(run.query, limit=limit)

        now = datetime.now(timezone.utc)
        next_index = await self._next_step_index(run_id)

        step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.SEARCHER,
            status=ResearchStepStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            input={"query": run.query, "limit": limit},
            output={"result_count": len(results), "provider": "duckduckgo_html"},
        )
        self.db.add(step)

        sources = [
            Source(
                run_id=run.id,
                url=r.url,
                title=r.title,
                raw_content=None,
                summary=None,
                relevance_score=None,
                extra_metadata={"provider": "duckduckgo_html"},
            )
            for r in results
        ]
        self.db.add_all(sources)

        await self._set_status_running_if_pending(run)

        await self.db.commit()
        await self.db.refresh(run)
        return run
    
    async def run_web_reader(self, run_id: UUID, limit: int = 5) -> ResearchRun:
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        has_search = await self._has_step_type(run_id, ResearchStepType.SEARCHER)
        if not has_search:
            raise InvalidPipelineStateError("Run search before reader.")

        already_read = await self._has_step_type(run_id, ResearchStepType.READER)
        if already_read:
            raise InvalidPipelineStateError("Reader has already been run for this research run.")

        result = await self.db.execute(select(Source).where(Source.run_id == run_id))
        sources = list(result.scalars().all())

        # Read only sources that don't have raw_content yet
        to_read = [s for s in sources if not s.raw_content][:limit]

        now = datetime.now(timezone.utc)
        next_index = await self._next_step_index(run_id)

        read_count = 0
        failed: list[dict[str, str]] = []

        for src in to_read:
            try:
                page = await fetch_html(src.url)
                text = extract_text_from_html(page.html)

                # Keep raw_content bounded so DB doesn't explode
                src.raw_content = text[:20_000]
                src.summary = basic_summary(text, max_chars=900)
                read_count += 1
            except (UnsafeUrlError, httpx.HTTPError, Exception) as exc:  # noqa: BLE001
                failed.append({"url": src.url, "error": str(exc)})

        step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.READER,
            status=ResearchStepStatus.COMPLETED,
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            input={"limit": limit},
            output={
                "attempted": len(to_read),
                "read_count": read_count,
                "failed_count": len(failed),
                "failed": failed[:10],
            },
        )
        self.db.add(step)

        await self.db.commit()
        await self.db.refresh(run)
        return run
    
    async def get_run_state(self, run_id: UUID) -> dict:
        run = await self.get_run_detail(run_id)

        # Map latest step per type
        latest_by_type: dict[ResearchStepType, ResearchStep] = {}
        for step in sorted(run.steps, key=lambda s: s.step_index):
            latest_by_type[step.step_type] = step

        steps: dict[ResearchStepType, dict] = {}
        for t in ResearchStepType:
            s = latest_by_type.get(t)
            if s is None:
                steps[t] = {
                    "status": ResearchStepStatus.PENDING,
                    "started_at": None,
                    "completed_at": None,
                    "error_message": None,
                }
            else:
                steps[t] = {
                    "status": s.status,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                    "error_message": s.error_message,
                }

        sources_with_summary = sum(1 for src in run.sources if (src.summary or "").strip())

        return {
            "run_id": run.id,
            "status": run.status,
            "steps": steps,
            "source_count": len(run.sources),
            "sources_with_summary": sources_with_summary,
        }
    
    async def execute(self, run_id: UUID, mode: ExecutionMode) -> ResearchRun:
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        started_at = datetime.now(timezone.utc)

        db_mode = DbExecutionMode.DUMMY if mode == ExecutionMode.DUMMY else DbExecutionMode.REAL

        started_event = PipelineEvent(
            run_id=run.id,
            event_type=PipelineEventType.STARTED,
            mode=db_mode,
            duration_ms=None,
            error_message=None,
        )
        self.db.add(started_event)
        await self.db.commit()

        try:
            if mode == ExecutionMode.DUMMY:
                await self.execute_dummy_pipeline(run_id)
            else:
                await self.execute_pipeline(run_id)

            duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

            completed_event = PipelineEvent(
                run_id=run.id,
                event_type=PipelineEventType.COMPLETED,
                mode=db_mode,
                duration_ms=duration_ms,
                error_message=None,
            )
            self.db.add(completed_event)
            await self.db.commit()

        except Exception as exc:  # noqa: BLE001
            # If the pipeline code threw after making DB changes, ensure session is usable
            await self.db.rollback()

            duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

            # Mark run failed (best-effort)
            run = await self.db.get(ResearchRun, run_id)
            if run is not None:
                run.status = ResearchRunStatus.FAILED
                run.error_message = str(exc)

            failed_event = PipelineEvent(
                run_id=run_id,
                event_type=PipelineEventType.FAILED,
                mode=db_mode,
                duration_ms=duration_ms,
                error_message=str(exc),
            )
            self.db.add(failed_event)
            await self.db.commit()

            raise

        return await self.get_run_detail(run_id)
    
    async def run_llm_synthesis(self, run_id: UUID) -> ResearchRun:
        run = await self.db.get(ResearchRun, run_id)
        if run is None:
            raise RunNotFoundError("Research run not found")

        already_synthesized = await self._has_step_type(run_id, ResearchStepType.SYNTHESIZER)
        if already_synthesized:
            raise InvalidPipelineStateError("Synthesis has already been run for this research run.")

        has_reader = await self._has_step_type(run_id, ResearchStepType.READER)
        if not has_reader:
            raise InvalidPipelineStateError("Run reader before synthesis.")

        # Load sources (prefer summaries; fall back to title/url)
        result = await self.db.execute(select(Source).where(Source.run_id == run_id))
        sources = list(result.scalars().all())

        if not sources:
            raise InvalidPipelineStateError("No sources available for synthesis.")

        # Build context from summaries (bounded)
        context_lines: list[str] = []
        for idx, src in enumerate(sources, start=1):
            title = src.title or src.url
            summ = (src.summary or "").strip()
            if not summ:
                summ = f"(No summary) {title}"
            context_lines.append(f"[{idx}] {title}\nURL: {src.url}\nSummary: {summ}\n")

        context = "\n".join(context_lines)
        context = context[:12_000]  # hard cap to keep prompt reasonable

        prompt = f"""You are an expert research assistant.
Given a research question and summaries of sources, produce a JSON object that matches this schema:

{{
  "summary": string,
  "key_points": [string, ...],
  "risks": [string, ...],
  "recommendation": string,
  "confidence": number  // 0.0 to 1.0
}}

Rules:
- Output MUST be valid JSON only. No markdown. No extra text.
- Use the sources' summaries as evidence.
- Be concise and practical.

Research question:
{run.query}

Sources:
{context}
"""

        # Get LLM client (Ollama by default)
        try:
            llm: LLMClient = get_llm_client()
        except Exception as exc:  # noqa: BLE001
            raise InvalidPipelineStateError(f"LLM client unavailable: {exc}")

        now = datetime.now(timezone.utc)
        next_index = await self._next_step_index(run_id)

        raw_completion = await llm.generate(prompt=prompt, options={"max_tokens": 900})

        # Parse JSON safely
        parsed: dict
        parse_error: str | None = None
        try:
            parsed = json.loads(raw_completion)
        except Exception as exc:  # noqa: BLE001
            parsed = {
                "summary": "Failed to parse model output as JSON.",
                "key_points": [],
                "risks": ["Model returned invalid JSON."],
                "recommendation": "Try running synthesis again or adjust prompt constraints.",
                "confidence": 0.2,
            }
            parse_error = str(exc)

        # Validate against schema (ensures stable structure)
        try:
            validated = SynthesisOutput.model_validate(parsed)
            output_payload = validated.model_dump()
        except Exception as exc:  # noqa: BLE001
            output_payload = {
                "summary": "Model output did not match required schema.",
                "key_points": [],
                "risks": ["Schema validation failed."],
                "recommendation": "Try running synthesis again or refine the prompt/schema.",
                "confidence": 0.2,
            }
            parse_error = f"{parse_error or ''} | schema_error={exc}".strip(" |")

        synth_step = ResearchStep(
            run_id=run.id,
            step_index=next_index,
            step_type=ResearchStepType.SYNTHESIZER,
            input={
                "source_ids": [str(s.id) for s in sources],
                "model_provider": run.model_provider,
            },
            output={
                **output_payload,
                "_meta": {
                    "raw_completion": raw_completion,
                    "parse_error": parse_error,
                    "source_count": len(sources),
                },
            },
        )
        self.db.add(synth_step)

        await self._set_status_completed(run)

        await self.db.commit()
        await self.db.refresh(run)
        return run