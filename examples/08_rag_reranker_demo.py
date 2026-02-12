# pyright: reportMissingImports=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""
Demo: RAG with LLM-based Reranking

Demonstrates why reranking helps: compare vector-only retrieval vs LLM reranking on an
adversarial doc set (high keyword overlap but low true relevance).
"""

import asyncio
import sys
from pathlib import Path
from typing import Final
from uuid import uuid4

from dotenv import load_dotenv

# pyright: ignore[reportMissingImports]
from qdrant_client import QdrantClient

from flare_ai_kit.agent import AgentSettings
from flare_ai_kit.common import SemanticSearchResult
from flare_ai_kit.rag.vector.api import (
    FixedSizeChunker,
    GeminiEmbedding,
    GeminiPointwiseReranker,
    LocalFileIndexer,
    QdrantRetriever,
    ingest_and_embed,
    upsert_to_qdrant,
)
from flare_ai_kit.rag.vector.settings import RerankerSettings, VectorDbSettings


def _print_results(
    title: str,
    results: list[SemanticSearchResult],
    *,
    show_reranker_scores: bool = False,
    max_text_chars: int = 96,
) -> None:
    print(f"\n{title} (top {len(results)}):\n")
    for i, res in enumerate(results, 1):
        source = res.metadata.get("file_name", "unknown")
        if show_reranker_scores:
            original_score = res.metadata.get("original_score", "N/A")
            reranker_score = res.metadata.get("reranker_score", "N/A")
            scores = f"orig={original_score}, rerank={reranker_score}/10"
        else:
            scores = f"vector={res.score:.3f}"
        preview = res.text.replace("\n", " ")[:max_text_chars]
        print(f"  {i:>2}. [{source}] ({scores})")
        print(f"      {preview}...")


def _hit_rate(results: list[SemanticSearchResult], relevant_sources: set[str]) -> int:
    return sum(1 for r in results if r.metadata.get("file_name") in relevant_sources)


async def main() -> None:  # noqa: PLR0915
    """Run the RAG + reranking demo."""
    load_dotenv()
    agent = AgentSettings()  # pyright: ignore[reportCallIssue]
    vector_db = VectorDbSettings(qdrant_batch_size=8)
    reranker_settings = RerankerSettings(enabled=True, score_threshold=5.0)

    if agent.gemini_api_key is None:
        print("GEMINI_API_KEY environment variable not set.")
        print("Please set the GEMINI_API_KEY environment variable to run this demo.")
        print("Example: export GEMINI_API_KEY='your_api_key_here'")
        sys.exit(1)

    demo_dir = Path("demo_rerank_data")
    demo_dir.mkdir(parents=True, exist_ok=True)

    # Intentionally include "keyword trap" docs that mention the right terms but are not helpful.
    documents: Final[list[tuple[str, str]]] = [
        (
            "how_to_reset_password.txt",
            "Password reset steps: On the login page, click 'Forgot Password'. "
            "Enter your email. Check your inbox for the reset link (valid for 24 hours). "
            "If the link expired, request a new one. If you still can't reset, contact support.",
        ),
        (
            "reset_link_expired.txt",
            "If your password reset link has expired: return to the login page, click 'Forgot Password', "
            "and request a new link. For security, links expire after 24 hours and can only be used once.",
        ),
        (
            "account_lockout_policy.txt",
            "Account lockout: after 5 failed login attempts, your account is locked for 15 minutes. "
            "Password reset does not unlock the account immediately. Wait 15 minutes or contact support.",
        ),
        (
            "billing_address_change.txt",
            "To change your billing address: go to Settings → Billing → Address, update fields, and Save. "
            "This does not change your login email or password.",
        ),
        (
            "two_factor_setup.txt",
            "Enable two-factor authentication (2FA): Settings → Security → Two-Factor. "
            "Scan the QR code in your authenticator app and enter the 6-digit code to confirm.",
        ),
        (
            "keyword_trap_marketing_blog.txt",
            "Password reset, reset password, forgot password, reset link, password reset email — "
            "we love talking about password reset in our marketing. This post resets expectations. "
            "It does not contain support steps, but it repeats password reset keywords many times. "
            "Password reset. Reset password. Forgot password. Reset link.",
        ),
        (
            "keyword_trap_shipping_reset.txt",
            "If your package tracking looks wrong, reset the tracking view in the shipping portal. "
            "This is unrelated to accounts, login, or password reset. It mentions reset and link and email.",
        ),
        (
            "password_requirements.txt",
            "Password requirements: 8+ chars, one uppercase, one lowercase, one number. "
            "If your password reset fails, ensure the new password meets requirements.",
        ),
        (
            "sso_login_note.txt",
            "If you signed up with Google/SSO, you may not have a password to reset. "
            "Use 'Continue with Google' or contact support to convert your account to email/password login.",
        ),
    ]

    try:
        for filename, content in documents:
            (demo_dir / filename).write_text(content, encoding="utf-8")

        print(f"Created {len(documents)} sample documents in {demo_dir}/\n")

        # Use larger chunks so each doc stays mostly intact for clearer ranking diffs.
        chunker = FixedSizeChunker(chunk_size=256)
        indexer = LocalFileIndexer(
            root_dir=str(demo_dir), chunker=chunker, allowed_extensions={".txt"}
        )

        embedding_model = GeminiEmbedding(
            api_key=agent.gemini_api_key.get_secret_value(),
            model=vector_db.embeddings_model,
            output_dimensionality=vector_db.embeddings_output_dimensionality,
        )

        data = ingest_and_embed(indexer, embedding_model, batch_size=8)
        print(f"Ingested and embedded {len(data)} chunks.\n")

        collection_name = f"reranker-demo-{uuid4().hex}"
        vector_size = 768
        upsert_to_qdrant(
            data,
            str(vector_db.qdrant_url),
            collection_name,
            vector_size,
            batch_size=vector_db.qdrant_batch_size,
        )
        print(
            f"Upserted {len(data)} vectors to Qdrant collection '{collection_name}'.\n"
        )

        client = QdrantClient(str(vector_db.qdrant_url))
        retriever = QdrantRetriever(client, embedding_model, vector_db)

        reranker = GeminiPointwiseReranker(
            api_key=agent.gemini_api_key.get_secret_value(),
            model=reranker_settings.model,
            num_batches=reranker_settings.num_batches,
            timeout_seconds=reranker_settings.timeout_seconds,
            score_threshold=reranker_settings.score_threshold,
        )

        scenarios: Final[list[tuple[str, str, set[str]]]] = [
            (
                "Reset password (needs actionable steps; keyword traps present)",
                "My password reset link expired. How do I get a new one?",
                {"how_to_reset_password.txt", "reset_link_expired.txt"},
            ),
            (
                "SSO edge case (vector overlap is misleading)",
                "I signed up with Google SSO. Why doesn't 'Forgot Password' work?",
                {"sso_login_note.txt"},
            ),
            (
                "Security settings (should prefer the exact setup steps)",
                "How do I enable two-factor authentication?",
                {"two_factor_setup.txt"},
            ),
        ]

        top_k_retrieve = 8
        top_k_show = 5
        for title, query, relevant_sources in scenarios:
            print("\n" + "=" * 80)
            print(f"{title}\nQuery: {query}")

            candidates = retriever.semantic_search(
                query, collection_name, top_k=top_k_retrieve
            )
            baseline = candidates[:top_k_show]

            _print_results("Vector-only results", baseline, show_reranker_scores=False)

            print("\nReranking with LLM...\n")
            reranked = await reranker.rerank(query, candidates, top_k=top_k_show)
            _print_results(
                "Reranked results",
                reranked,
                show_reranker_scores=True,
            )

            base_hits = _hit_rate(baseline, relevant_sources)
            rerank_hits = _hit_rate(reranked, relevant_sources)
            print("\nSummary:")
            print(f"  - Relevant sources: {sorted(relevant_sources)}")
            print(
                f"  - Hit@{top_k_show}: vector-only={base_hits}/{top_k_show}, reranked={rerank_hits}/{top_k_show}"
            )

        print("\n" + "=" * 80)
        print("Demo complete.")
        print(
            f"Notes: reranker score threshold={reranker_settings.score_threshold}, "
            f"batches={reranker_settings.num_batches}, timeout={reranker_settings.timeout_seconds}s"
        )
    finally:
        for filename, _ in documents:
            (demo_dir / filename).unlink(missing_ok=True)
        demo_dir.rmdir()


if __name__ == "__main__":
    asyncio.run(main())
