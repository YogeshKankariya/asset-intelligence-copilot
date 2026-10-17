"""Document Retrieval and Evidence Grounding Module for Asset Intelligence Copilot.

Provides a lightweight, transparent, local lexical search layer (BM25) over:
- Well manuals (T200.md, T350.md)
- Standard Operating Procedures (field-work-sop.md, spill-response-sop.md, regulatory-compliance-sop.md)
- Asset maintenance reports (maintenance-reports/*.md)
- Asset operational notes (context.jsonl), regulatory events (regulatory-events.jsonl), and metadata.

Preserves exact source provenance, section titles, record IDs, and timestamps.
Does not require external APIs or vector databases.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    source_path: str  # relative to dataset root
    title: str | None
    section: str | None
    content: str
    record_id: str | None = None
    timestamp: str | None = None
    asset_id: str | None = None
    doc_type: str = "document"  # "manual", "sop", "maintenance_report", "context_note", "regulatory_event", "metadata"


def _clean_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load_and_chunk_markdown(
    file_path: Path,
    dataset_root: Path,
    asset_id: str | None = None,
    doc_type: str = "document",
) -> list[DocumentChunk]:
    """Loads and splits a markdown file into section-based DocumentChunks."""
    if not file_path.is_file():
        return []

    try:
        raw_text = file_path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []

    text = _clean_text(raw_text).strip()
    if not text:
        return []

    try:
        rel_path = file_path.relative_to(dataset_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    lines = text.split("\n")

    # Determine document title from the first header or filename
    doc_title = file_path.stem
    for line in lines:
        if line.startswith("# "):
            doc_title = line[2:].strip()
            break

    # Split into sections based on markdown headers (# , ## , ### )
    sections: list[tuple[str, list[str]]] = []
    current_heading = doc_title
    current_lines: list[str] = []

    for line in lines:
        if re.match(r"^#{1,3}\s+", line):
            if current_lines:
                sections.append((current_heading, current_lines))
                current_lines = []
            current_heading = line.strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    chunks: list[DocumentChunk] = []
    chunk_counter = 0

    for heading, sec_lines in sections:
        body = "\n".join(sec_lines).strip()
        if not body and heading.startswith("#"):
            continue

        full_sec_text = f"{heading}\n\n{body}" if body else heading

        # Extract potential record/protocol IDs from heading or body (e.g. WS-05, MNT-0001-002, SR-01, RC-02)
        id_match = re.search(
            r"\b(WS-\d{2}|SR-\d{2}|RC-\d{2}|MNT-[\w-]+|INS-[\w-]+|OM-[\w-]+|T\d{3})\b",
            full_sec_text,
            re.IGNORECASE,
        )
        rec_id = id_match.group(1).upper() if id_match else None

        # Check timestamp if available in body (e.g. "Work started: 17 Mar 2023", "2026-05-01")
        time_match = re.search(r"\b(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z?)?)\b", body)
        rec_time = time_match.group(1) if time_match else None

        # If this section contains protocol table rows (e.g. | **WS-05** | ... |), extract each protocol as a focused chunk
        protocol_rows = re.findall(
            r"\|\s*\*\*([A-Z]+-\d{2})\*\*\s*\|\s*([^\|]+)\|",
            body,
        )
        for proto_id, proto_req in protocol_rows:
            chunk_counter += 1
            proto_text = f"{doc_title} — {heading}\n\nProtocol {proto_id}: {proto_req.strip()}"
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#{proto_id}",
                    source_path=rel_path,
                    title=doc_title,
                    section=f"{heading} ({proto_id})",
                    content=proto_text,
                    record_id=proto_id,
                    timestamp=rec_time,
                    asset_id=asset_id,
                    doc_type="sop" if "sop" in doc_type.lower() else doc_type,
                )
            )

        # If section is reasonably sized (<= 1400 chars), keep as one chunk
        if len(full_sec_text) <= 1400:
            chunk_counter += 1
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#chunk{chunk_counter}",
                    source_path=rel_path,
                    title=doc_title,
                    section=heading,
                    content=full_sec_text,
                    record_id=rec_id,
                    timestamp=rec_time,
                    asset_id=asset_id,
                    doc_type=doc_type,
                )
            )
        else:
            # Split longer sections into overlapping paragraph chunks
            paragraphs = body.split("\n\n")
            current_para_chunk: list[str] = []
            curr_len = 0

            for para in paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue

                if curr_len + len(para_clean) > 1000 and current_para_chunk:
                    chunk_counter += 1
                    chunk_content = f"{heading}\n\n" + "\n\n".join(current_para_chunk)
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{rel_path}#chunk{chunk_counter}",
                            source_path=rel_path,
                            title=doc_title,
                            section=heading,
                            content=chunk_content,
                            record_id=rec_id,
                            timestamp=rec_time,
                            asset_id=asset_id,
                            doc_type=doc_type,
                        )
                    )
                    # Keep last paragraph for overlap
                    current_para_chunk = [current_para_chunk[-1], para_clean]
                    curr_len = len(current_para_chunk[0]) + len(para_clean)
                else:
                    current_para_chunk.append(para_clean)
                    curr_len += len(para_clean)

            if current_para_chunk:
                chunk_counter += 1
                chunk_content = f"{heading}\n\n" + "\n\n".join(current_para_chunk)
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{rel_path}#chunk{chunk_counter}",
                        source_path=rel_path,
                        title=doc_title,
                        section=heading,
                        content=chunk_content,
                        record_id=rec_id,
                        timestamp=rec_time,
                        asset_id=asset_id,
                        doc_type=doc_type,
                    )
                )

    return chunks


def load_context_jsonl_chunks(
    file_path: Path,
    dataset_root: Path,
    asset_id: str | None = None,
) -> list[DocumentChunk]:
    """Extracts operational context notes and corrections as DocumentChunks."""
    if not file_path.is_file():
        return []

    try:
        rel_path = file_path.relative_to(dataset_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    chunks: list[DocumentChunk] = []
    line_num = 0

    try:
        with file_path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                line_num += 1
                try:
                    record = json.loads(line_str)
                except json.JSONDecodeError:
                    continue

                if not isinstance(record, dict):
                    continue

                note_id = record.get("note_id") or f"NOTE-{line_num}"
                note_type = record.get("note_type", "operator_note")
                text = record.get("text", "")
                author = record.get("author", "operator")
                timestamp = record.get("timestamp") or record.get("created_at")
                target_iid = record.get("inspection_id")
                aid = asset_id or record.get("asset_id")
                header_parts = [f"Context Note {note_id} ({note_type})"]
                if aid:
                    header_parts.append(f"Asset: {aid}")
                if target_iid:
                    header_parts.append(f"Target Inspection: {target_iid}")
                if timestamp:
                    header_parts.append(f"Recorded at: {timestamp}")
                if author:
                    header_parts.append(f"Author: {author}")

                content = " · ".join(header_parts) + "\n" + f"Note text: {text}"

                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{rel_path}#{note_id}",
                        source_path=rel_path,
                        title=f"Context Note {note_id}",
                        section=f"Note Type: {note_type}",
                        content=content,
                        record_id=note_id,
                        timestamp=timestamp,
                        asset_id=aid,
                        doc_type="context_note",
                    )
                )
    except OSError:
        return []

    return chunks


def load_regulatory_events_chunks(
    file_path: Path,
    dataset_root: Path,
    asset_id: str | None = None,
) -> list[DocumentChunk]:
    """Extracts regulatory compliance events as DocumentChunks."""
    if not file_path.is_file():
        return []

    try:
        rel_path = file_path.relative_to(dataset_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    chunks: list[DocumentChunk] = []
    line_num = 0

    try:
        with file_path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                line_num += 1
                try:
                    record = json.loads(line_str)
                except json.JSONDecodeError:
                    continue

                if not isinstance(record, dict):
                    continue

                event_id = record.get("event_id") or f"REG-{line_num}"
                event_type = record.get("event_type", "regulatory_event")
                date = record.get("date") or record.get("timestamp")
                desc = record.get("description", "")
                rel_iid = record.get("related_inspection_id")

                content_parts = [
                    f"Regulatory Event {event_id} ({event_type}) on {date}",
                ]
                if rel_iid:
                    content_parts.append(f"Related Inspection: {rel_iid}")
                content_parts.append(f"Description: {desc}")

                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{rel_path}#{event_id}",
                        source_path=rel_path,
                        title=f"Regulatory Event {event_id}",
                        section=event_type,
                        content="\n".join(content_parts),
                        record_id=event_id,
                        timestamp=date,
                        asset_id=asset_id or record.get("asset_id"),
                        doc_type="regulatory_event",
                    )
                )
    except OSError:
        return []

    return chunks


def load_metadata_chunk(
    file_path: Path,
    dataset_root: Path,
    asset_id: str | None = None,
) -> list[DocumentChunk]:
    """Extracts asset metadata summary as a DocumentChunk."""
    if not file_path.is_file():
        return []

    try:
        raw_text = file_path.read_text(encoding="utf-8-sig", errors="replace")
        data = json.loads(raw_text)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, dict):
        return []

    try:
        rel_path = file_path.relative_to(dataset_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    aid = data.get("asset_id") or asset_id or "UNKNOWN"
    name = data.get("name", "")
    well_type = data.get("well_type", "")
    area = data.get("area_id", "")
    equipment = data.get("equipment", [])

    eq_summary = []
    if isinstance(equipment, list):
        for eq in equipment:
            if isinstance(eq, dict):
                eq_summary.append(f"- {eq.get('kind', 'equipment')}: {eq.get('model', 'unknown')}")

    lines = [
        f"Well Metadata for {aid} ({name})",
        f"Well type: {well_type}, Area: {area}",
    ]
    if eq_summary:
        lines.append("Installed Equipment:")
        lines.extend(eq_summary)

    return [
        DocumentChunk(
            chunk_id=f"{rel_path}#metadata",
            source_path=rel_path,
            title=f"Metadata for {aid}",
            section="Asset Metadata & Equipment",
            content="\n".join(lines),
            record_id=None,
            asset_id=aid,
            doc_type="metadata",
        )
    ]


class DocumentCorpus:
    """Loads and caches document chunks for BM25 retrieval."""

    def __init__(self, dataset_root: Path):
        self.dataset_root = dataset_root
        self._cached_chunks: dict[str, list[DocumentChunk]] = {}

    def get_chunks(self, asset_id: str | None = None) -> list[DocumentChunk]:
        """Loads chunks for fleet manuals/SOPs plus the target asset if specified."""
        cache_key = asset_id or "__all_fleet__"
        if cache_key in self._cached_chunks:
            return self._cached_chunks[cache_key]

        chunks: list[DocumentChunk] = []
        sample_data = self.dataset_root / "sample-data"
        if not sample_data.is_dir():
            sample_data = self.dataset_root

        # 1. Global Fleet Manuals
        well_types_dir = sample_data / "fleet" / "well-types"
        if well_types_dir.is_dir():
            for f in well_types_dir.glob("*.md"):
                chunks.extend(
                    load_and_chunk_markdown(f, self.dataset_root, asset_id=None, doc_type="manual")
                )

        # 2. Global Fleet SOPs
        sops_dir = sample_data / "fleet" / "sops"
        if sops_dir.is_dir():
            for f in sops_dir.glob("*.md"):
                chunks.extend(
                    load_and_chunk_markdown(f, self.dataset_root, asset_id=None, doc_type="sop")
                )

        # 3. Asset-specific documents
        assets_dir = sample_data / "assets"
        if assets_dir.is_dir():
            target_asset_dirs = []
            if asset_id and (assets_dir / asset_id).is_dir():
                target_asset_dirs = [assets_dir / asset_id]
            else:
                # If no asset_id specified and corpus is small (e.g. test fixture <= 10 assets), load all
                all_subdirs = [p for p in assets_dir.iterdir() if p.is_dir()]
                if len(all_subdirs) <= 10:
                    target_asset_dirs = all_subdirs

            for a_dir in target_asset_dirs:
                aid = a_dir.name
                # Metadata
                chunks.extend(load_metadata_chunk(a_dir / "metadata.json", self.dataset_root, asset_id=aid))
                # Context notes
                chunks.extend(load_context_jsonl_chunks(a_dir / "context.jsonl", self.dataset_root, asset_id=aid))
                # Regulatory events
                chunks.extend(load_regulatory_events_chunks(a_dir / "regulatory-events.jsonl", self.dataset_root, asset_id=aid))
                # Maintenance reports
                mnt_dir = a_dir / "maintenance-reports"
                if mnt_dir.is_dir():
                    for mf in mnt_dir.glob("*.md"):
                        chunks.extend(
                            load_and_chunk_markdown(mf, self.dataset_root, asset_id=aid, doc_type="maintenance_report")
                        )

        self._cached_chunks[cache_key] = chunks
        return chunks


STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "could", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me", "more",
    "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "yours", "yourself", "yourselves", "tell",
    "give", "show", "please", "can",
}


class BM25Retriever:
    """Local, lightweight Okapi BM25 index and search engine."""

    def __init__(self, chunks: list[DocumentChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.corpus_size = len(chunks)
        self.doc_lens: list[int] = []
        self.doc_token_counts: list[dict[str, int]] = []
        self.df: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.avg_doc_len = 0.0

        self._build_index()

    @staticmethod
    def _stem(word: str) -> str:
        w = word.lower()
        for suffix in ("ation", "ations", "ing", "ings", "ied", "ies", "ed", "es", "ment", "ments", "ance", "ence", "able", "ible", "al"):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                return w[:-len(suffix)]
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            return w[:-1]
        return w

    @classmethod
    def tokenize(cls, text: str) -> list[str]:
        raw_tokens = re.findall(r"[a-zA-Z0-9_\-\.]+", text.lower())
        tokens = []
        for t in raw_tokens:
            cleaned = t.strip("-._")
            if cleaned:
                tokens.append(cleaned)
                stem = cls._stem(cleaned)
                if stem != cleaned:
                    tokens.append(stem)
                if "-" in cleaned:
                    tokens.append(cleaned.replace("-", ""))
        return tokens

    def _build_index(self) -> None:
        if not self.chunks:
            return

        total_tokens = 0
        for chunk in self.chunks:
            text = f"{chunk.title or ''} {chunk.section or ''} {chunk.record_id or ''} {chunk.asset_id or ''} {chunk.content}"
            toks = self.tokenize(text)
            d_len = len(toks)
            self.doc_lens.append(d_len)
            total_tokens += d_len

            counts: dict[str, int] = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            self.doc_token_counts.append(counts)

            for t in counts:
                self.df[t] = self.df.get(t, 0) + 1

        self.avg_doc_len = total_tokens / self.corpus_size if self.corpus_size > 0 else 0.0

        for t, freq in self.df.items():
            # BM25 IDF with smoothing
            self.idf[t] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def search(
        self,
        query: str,
        asset_id: str | None = None,
        top_k: int = 5,
        min_score: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Searches indexed chunks using BM25 with identifier and asset boosting."""
        if not self.chunks:
            return []

        all_toks = self.tokenize(query)
        q_tokens = [t for t in all_toks if t not in STOPWORDS]
        if not q_tokens:
            return []

        # Ensure at least one query token exists in the corpus vocabulary
        matching_vocab = [t for t in q_tokens if t in self.df]
        if not matching_vocab:
            return []

        # Exact document/record identifiers (e.g. WS-05, MNT-0001-002, SR-01, RC-02, T200, T350, NOTE-001)
        exact_ids = {
            tok
            for tok in q_tokens
            if re.match(r"^(ins|mnt|ws|sr|rc|om|t\d{3}|note|reg)", tok) and not tok.startswith("well")
        }

        q_lower = query.lower()

        scores: list[float] = [0.0] * self.corpus_size

        for i, chunk in enumerate(self.chunks):
            counts = self.doc_token_counts[i]
            d_len = self.doc_lens[i]
            score = 0.0

            for q_tok in q_tokens:
                if q_tok in counts:
                    tf = counts[q_tok]
                    idf = self.idf.get(q_tok, 0.0)
                    denom = tf + self.k1 * (
                        1.0 - self.b + self.b * (d_len / self.avg_doc_len if self.avg_doc_len > 0 else 1.0)
                    )
                    score += idf * (tf * (self.k1 + 1.0)) / denom

            # Identifier matching boost
            for eid in exact_ids:
                if (
                    (chunk.record_id and eid in chunk.record_id.lower())
                    or (chunk.section and eid in chunk.section.lower())
                    or (chunk.title and eid in chunk.title.lower())
                    or (eid in counts)
                ):
                    score += 6.0

            # Document type intent boosting
            if ("note" in q_lower or "context" in q_lower) and chunk.doc_type == "context_note":
                score += 3.0
            elif ("sop" in q_lower or "protocol" in q_lower or "procedure" in q_lower) and chunk.doc_type == "sop":
                score += 3.0
            elif ("manual" in q_lower or "specification" in q_lower) and chunk.doc_type == "manual":
                score += 3.0
            elif ("maintenance report" in q_lower or "repair report" in q_lower) and chunk.doc_type == "maintenance_report":
                score += 3.0
            elif "metadata" in q_lower and chunk.doc_type == "metadata":
                score += 3.0
            elif ("regulatory" in q_lower or "compliance event" in q_lower) and chunk.doc_type == "regulatory_event":
                score += 3.0

            # Asset preference weighting
            if asset_id:
                target_aid = asset_id.lower()
                if chunk.asset_id and chunk.asset_id.lower() == target_aid:
                    score *= 1.35
                elif chunk.asset_id is None:
                    # Global manual or SOP - preserve score
                    score *= 1.0
                else:
                    # Belongs to a different asset - downweight
                    score *= 0.2

            scores[i] = score

        scored_pairs = [
            (i, scores[i]) for i in range(self.corpus_size) if scores[i] >= min_score
        ]
        # Deterministic sort: descending by score, ascending by original chunk index
        scored_pairs.sort(key=lambda x: (-x[1], x[0]))

        results: list[dict[str, Any]] = []
        for rank, (idx, score) in enumerate(scored_pairs[:top_k], start=1):
            chunk = self.chunks[idx]
            results.append(
                {
                    "source": chunk.source_path,
                    "document_title": chunk.title,
                    "section": chunk.section,
                    "record_id": chunk.record_id,
                    "timestamp": chunk.timestamp,
                    "asset_id": chunk.asset_id,
                    "doc_type": chunk.doc_type,
                    "excerpt": chunk.content.strip(),
                    "score": round(score, 3),
                    "rank": rank,
                }
            )

        return results


def detect_documentary_conflicts(
    retrieved_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Detects documentary conflicts and explicit corrections among retrieved passages."""
    conflicts: list[dict[str, Any]] = []

    # Check for context correction notes targeting another retrieved record
    for r in retrieved_results:
        if r.get("doc_type") == "context_note":
            excerpt = r.get("excerpt", "")
            rec_id = r.get("record_id")
            # Look for targeted IDs in note
            matched_targets = re.findall(r"\b(INS-[\w-]+|MNT-[\w-]+|WELL-[\w-]+)\b", excerpt)
            for target in matched_targets:
                if any(other.get("record_id") == target for other in retrieved_results if other != r):
                    conflicts.append(
                        {
                            "field": "documentary_evidence",
                            "source": r.get("source"),
                            "description": (
                                f"Correction note {rec_id} explicitly qualifies or clarifies record {target}: "
                                f"'{excerpt.splitlines()[-1] if excerpt else ''}'"
                            ),
                            "resolution": "correction_note_supercedes_or_clarifies_record",
                            "is_resolved": True,
                        }
                    )

    # Check for cross-manual threshold divergences (e.g. T200 vs T350 rules)
    has_t200 = any("T200" in (r.get("document_title") or "") for r in retrieved_results)
    has_t350 = any("T350" in (r.get("document_title") or "") for r in retrieved_results)
    if has_t200 and has_t350:
        conflicts.append(
            {
                "field": "manual_specifications",
                "source": "fleet/well-types",
                "description": (
                    "Retrieved guidance spans both T200 and T350 manuals, which specify different "
                    "operating limits (e.g. 15°C production threshold and 85°C alarm for T200 vs. "
                    "20°C production threshold and 95°C alarm for T350)."
                ),
                "resolution": "well_type_specific_manual_governs",
                "is_resolved": True,
            }
        )

    unresolved = any(not c.get("is_resolved", True) for c in conflicts)
    return conflicts, unresolved


def retrieve_documents(
    query: str,
    asset_id: str | None = None,
    dataset_root: Path | None = None,
    top_k: int = 5,
    min_score: float = 1.0,
) -> list[dict[str, Any]]:
    """High-level function to retrieve relevant passages from the dataset."""
    from app.operational_intelligence import DATASET_ROOT

    root = dataset_root or DATASET_ROOT
    corpus = DocumentCorpus(root)
    chunks = corpus.get_chunks(asset_id=asset_id)
    retriever = BM25Retriever(chunks)
    return retriever.search(query=query, asset_id=asset_id, top_k=top_k, min_score=min_score)
