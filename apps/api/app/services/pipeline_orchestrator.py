from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
import json
import httpx
import re

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

        # Load sources for this run
        result = await self.db.execute(select(Source).where(Source.run_id == run_id))
        sources = list(result.scalars().all())

        # Read only sources that don't have raw_content yet
        to_read = [s for s in sources if not s.raw_content][:limit]

        now = datetime.now(timezone.utc)
        next_index = await self._next_step_index(run_id)

        read_count = 0
        failed: list[dict[str, str]] = []

        if not to_read:
            step = ResearchStep(
                run_id=run.id,
                step_index=next_index,
                step_type=ResearchStepType.READER,
                status=ResearchStepStatus.COMPLETED,
                started_at=now,
                completed_at=datetime.now(timezone.utc),
                input={"limit": limit},
                output={
                    "attempted": 0,
                    "read_count": 0,
                    "failed_count": 0,
                    "failed": [],
                    "notes": "No unread sources found.",
                },
            )
            self.db.add(step)
            await self.db.commit()
            await self.db.refresh(run)
            return run

        # --- concurrent read with bounded parallelism ---
        import asyncio  # local import to keep file minimal

        semaphore = asyncio.Semaphore(4)  # keep it small; avoids hammering sites

        async def read_one(src: Source, client: httpx.AsyncClient) -> None:
            nonlocal read_count

            async with semaphore:
                try:
                    page = await fetch_html(src.url, client=client)
                    text = extract_text_from_html(page.html)

                    # Keep raw_content bounded so DB doesn't explode
                    cleaned = (text or "").strip()
                    if not cleaned:
                        raise ValueError("Empty extracted text")

                    src.raw_content = cleaned[:20_000]
                    src.summary = basic_summary(cleaned, max_chars=900)
                    read_count += 1

                except (UnsafeUrlError, httpx.HTTPError, ValueError) as exc:
                    failed.append({"url": src.url, "error": str(exc)})
                except Exception as exc:  # noqa: BLE001
                    failed.append({"url": src.url, "error": f"Unexpected error: {exc}"})

        headers = {"User-Agent": "InquiryOS/0.1 (+https://localhost)"}  # safe default

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            await asyncio.gather(*(read_one(s, client) for s in to_read))

        # Mark step status: completed even if partial, but record failures
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

        stage: str | None = None

        try:
            if mode == ExecutionMode.DUMMY:
                stage = "execute_dummy_pipeline"
                await self.execute_dummy_pipeline(run_id)
            else:
                stage = "execute_pipeline"
                await self.execute_pipeline(run_id)

            duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

            completed_event = PipelineEvent(
                run_id=run.id,
                event_type=PipelineEventType.COMPLETED,
                mode=db_mode,
                stage=stage,
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
                stage=stage,
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

        # Build evidence context (prefer raw_content; fall back to summary)
        def _compact(text: str, max_chars: int) -> str:
            t = (text or "").strip()
            if len(t) <= max_chars:
                return t
            return t[: max_chars - 20].rstrip() + " ...[truncated]"

        context_lines: list[str] = []
        for idx, src in enumerate(sources, start=1):
            title = (src.title or src.url).strip()
            summary = (src.summary or "").strip()
            raw = (src.raw_content or "").strip()

            # Prefer raw_content, but keep it bounded (this is the real upgrade)
            evidence_text = raw if raw else summary
            if not evidence_text:
                evidence_text = "(No content available for this source.)"

            # Create a small “snippet pack” the model can cite
            evidence_compact = _compact(evidence_text, 1800)

            context_lines.append(
                "\n".join(
                    [
                        f"[{idx}] {title}",
                        f"URL: {src.url}",
                        f"EVIDENCE (use for citations): {evidence_compact}",
                    ]
                )
            )

        context = "\n\n".join(context_lines)

        # Hard cap to keep prompt reasonable (token/cost control)
        context = _compact(context, 14_000)

        prompt = f"""You are an expert research assistant.

        Your job:
        - Answer the research question using ONLY the evidence excerpts below.
        - Every key point and every risk MUST include citations like [1], [2], etc.
        - Prefer citing the most relevant sources; don't cite if you truly have no evidence.

        Return a JSON object that matches EXACTLY this schema:

        {{
        "summary": string,
        "key_points": [string, ...],
        "risks": [string, ...],
        "recommendation": string,
        "confidence": number
        }}

        Rules:
        - Output MUST be valid JSON only. No markdown. No extra text.
        - Put citations directly inside the strings, e.g. "X is true because ... [1][3]"
        - Confidence must be 0.0 to 1.0

        Research question:
        {run.query}

        Evidence sources:
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

        # --- Citation enforcement + coverage scoring ---
        citation_pattern = re.compile(r"\[\d+\]")

        def _has_citation(text: str) -> bool:
            return bool(citation_pattern.search(text))

        key_points = output_payload.get("key_points", [])
        risks = output_payload.get("risks", [])

        missing_citations: list[str] = []

        for idx, point in enumerate(key_points):
            if isinstance(point, str) and not _has_citation(point):
                missing_citations.append(f"key_points[{idx}]")

        for idx, risk in enumerate(risks):
            if isinstance(risk, str) and not _has_citation(risk):
                missing_citations.append(f"risks[{idx}]")

        if missing_citations:
            output_payload["confidence"] = min(output_payload.get("confidence", 0.5), 0.3)
            output_payload.setdefault("_warnings", []).append(
                {"type": "missing_citations", "fields": missing_citations}
            )

        # Coverage: how many unique sources were cited?
        source_count = len(sources)
        cited_indices: set[int] = set()

        combined_texts = []
        if isinstance(key_points, list):
            combined_texts.extend(key_points)
        if isinstance(risks, list):
            combined_texts.extend(risks)

        for text in combined_texts:
            if not isinstance(text, str):
                continue
            for m in re.findall(r"\[(\d+)\]", text):
                try:
                    n = int(m)
                except ValueError:
                    continue
                if 1 <= n <= source_count:
                    cited_indices.add(n)

        coverage_ratio = (len(cited_indices) / source_count) if source_count > 0 else 0.0

        # Put metrics into meta so UI can show it later
        output_payload.setdefault("_meta", {})
        output_payload["_meta"]["unique_sources_cited"] = len(cited_indices)
        output_payload["_meta"]["coverage_ratio"] = coverage_ratio

        if source_count >= 3 and coverage_ratio < 0.4:
            output_payload["confidence"] = min(output_payload.get("confidence", 0.5), 0.4)
            output_payload.setdefault("_warnings", []).append(
                {"type": "low_source_coverage", "coverage_ratio": coverage_ratio}
            )
            
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