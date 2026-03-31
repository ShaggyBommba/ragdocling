from pydantic import BaseModel
from qdrant_client.http.models import ScoredPoint

from dacke.domain.values.pipeline import PipelineID
from dacke.domain.values.retrieval import RerankerSettings


class RetrieveRequestBody(BaseModel):
    query: str
    top_k: int = 5
    reranker: RerankerSettings | None = None
    expand_links: bool = True
    tags: list[str] | None = None
    origins: list[str] | None = None


class RetrieveDTO(BaseModel):
    pipeline_id: PipelineID
    query: str
    top_k: int = 5
    reranker: RerankerSettings | None = None
    expand_links: bool = True
    tags: list[str] | None = None
    origins: list[str] | None = None


def _build_formatted_text(
    raw_text: str,
    score: float,
    title: str | None,
    origin: str,
    pages: int | None,
    tags: list[str],
    attachments: list[dict[str, str]],
    index: int = 1,
    total: int = 1,
) -> str:
    # Result header (top-level, one #)
    header = f"# Result {index}/{total}  (score: {score:.4f})"

    meta_lines: list[str] = ["---"]
    if origin:
        meta_lines.append(f"origin: {origin}")
    if pages is not None:
        meta_lines.append(f"pages: {pages}")
    if tags:
        meta_lines.append(f"tags: [{', '.join(tags)}]")
    meta_lines.append("---")
    frontmatter = "\n".join(meta_lines)

    if title:
        body = f"## {title}\n\n{raw_text}"
    else:
        body = raw_text

    if attachments:
        attachment_lines = ["## Attachments"]
        for att in attachments:
            ref = att.get("reference")
            desc = att.get("description", "Description not available").strip().lower()
            filename = ref.split("/")[-1] if ref else "unknown"

            if ref:
                attachment_lines.append(f"### {filename}")
                attachment_lines.append(f"{desc}({ref})")
        body = body + "\n\n" + "\n".join(attachment_lines)

    return f"{header}\n{frontmatter}\n{body}\n\n"


class RetrieveResultDTO(BaseModel):
    score: float
    text: str
    title: str | None
    pages: int | None
    origin: str
    attachments: list[dict[str, str]]

    @classmethod
    def from_point(
        cls,
        point: ScoredPoint,
        index: int = 1,
        total: int = 1,
        score_override: float | None = None,
    ) -> "RetrieveResultDTO":
        payload = point.payload or {}
        score = score_override if score_override is not None else point.score
        title = payload.get("title")
        origin = payload.get("origin", "")
        pages = payload.get("pages")
        tags: list[str] = payload.get("tags") or []
        attachments: list[dict[str, str]] = payload.get("attachments", [])
        raw_text: str = payload.get("text", "")

        formatted = _build_formatted_text(
            raw_text=raw_text,
            score=score,
            title=title,
            origin=origin,
            pages=pages,
            tags=tags,
            attachments=attachments,
            index=index,
            total=total,
        )

        return cls(
            score=score,
            text=formatted,
            title=title,
            pages=pages,
            origin=origin,
            attachments=attachments,
        )
