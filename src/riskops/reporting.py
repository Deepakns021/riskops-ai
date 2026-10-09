from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewDraft:
    user: str
    day: str
    score: float
    evidence: dict[str, float]


def make_review_draft(item: ReviewDraft) -> str:
    """Grounded report draft: contains only provided evidence, not model speculation."""
    evidence_lines = "\n".join(f"- {key.replace('_', ' ')}: {value:g}" for key, value in item.evidence.items())
    return f"""# Analyst review draft — human approval required

**Subject:** `{item.user}`  
**Observed day:** `{item.day}`  
**Anomaly score:** `{item.score:.4f}` (ranking signal, not a finding of wrongdoing)

## Observed evidence
{evidence_lines}

## Suggested analyst questions
- Is the activity consistent with an approved role, project, schedule, or exception?
- Are timestamps, event completeness, and identity mappings reliable for this day?
- Does corroborating evidence justify any further review under the organization’s policy?

## Required human disposition
- [ ] Reviewed evidence and context
- [ ] False positive / benign explanation recorded
- [ ] Escalation approved under policy

This is a research benchmark workflow using synthetic CERT data. Do not take automated employment, access, or disciplinary action from this draft.
"""
