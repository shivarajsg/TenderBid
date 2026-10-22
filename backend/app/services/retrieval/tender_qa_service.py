import logging
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.tenders import TenderRepository
from app.schemas.evidence import EvidenceCitation
from app.schemas.tender import QACitation, TenderQAResponse
from app.services.ai.gemini_client import GeminiClient, get_gemini_client
from app.services.retrieval.citation_validator import CitationValidator
from app.services.retrieval.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


class TenderQAService:
    """
    Grounded question-answering service strictly scoped to an individual tender's documents.
    Uses Hybrid RAG (PostgreSQL lexical + ChromaDB semantic) and validates citations against
    physical document metadata before synthesizing answers.
    """

    def __init__(
        self,
        session: AsyncSession,
        hybrid_retriever: Optional[HybridRetriever] = None,
        citation_validator: Optional[CitationValidator] = None,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.session = session
        self.repository = TenderRepository(session)
        self.retriever = hybrid_retriever or HybridRetriever(session)
        self.validator = citation_validator or CitationValidator(session)
        self.gemini = gemini_client or get_gemini_client()

    async def answer_question(
        self,
        tender_id: uuid.UUID,
        question: str,
    ) -> TenderQAResponse:
        """
        Retrieve tender document evidence, validate citation provenance,
        and generate a grounded, verifiable answer.
        """
        tender = await self.repository.get_by_id(tender_id)
        if not tender:
            return TenderQAResponse(
                tender_id=tender_id,
                question=question,
                answer=f"Tender with ID '{tender_id}' not found.",
                status="ERROR",
                confidence="LOW",
                citations=[],
            )

        # 1. Hybrid search scoped exclusively to this tender (company_id=None prevents vault access)
        raw_citations: List[EvidenceCitation] = await self.retriever.search(
            query=question,
            tender_id=tender.id,
            company_id=None,
            limit=5,
        )

        # 2. Strict citation validation (tender scoping and page boundary checks)
        # Using a dummy company_id (UUID 0) ensures only documents belonging to this tender pass
        dummy_company_id = uuid.UUID(int=0)
        valid_citations, warnings = await self.validator.validate_citations(
            citations=raw_citations,
            authorized_tender_id=tender.id,
            authorized_company_id=dummy_company_id,
        )

        # 3. Handle cases where no evidence could be retrieved or verified
        if not valid_citations:
            return TenderQAResponse(
                tender_id=tender.id,
                question=question,
                answer=(
                    "The attached tender notices and RFP documents do not contain verifiable "
                    "information answering this question. No matching document evidence was found."
                ),
                status="INSUFFICIENT_EVIDENCE",
                confidence="LOW",
                citations=[],
            )

        # 4. Synthesize grounded answer
        answer_text = ""
        qa_citations: List[QACitation] = []
        for cit in valid_citations:
            qa_citations.append(
                QACitation(
                    document_id=cit.document_id,
                    source_filename=cit.source_filename,
                    page_number=cit.page_number,
                    supporting_excerpt=cit.excerpt,
                )
            )

        if self.gemini.is_configured():
            context_blocks = "\n\n".join(
                f"[Document: {c.source_filename} | Page {c.page_number}]\n{c.supporting_excerpt}"
                for c in qa_citations
            )
            prompt = (
                f"Tender Title: {tender.title}\n"
                f"Tender Reference: {tender.tender_reference}\n"
                f"User Question: {question}\n\n"
                "You are an objective procurement compliance assistant. "
                "Answer the user's question using ONLY the provided excerpts from the tender document. "
                "Cite the exact document name and page number for each point. "
                "If the excerpts do not directly address the question, clearly state that the tender does not specify. "
                "Never hallucinate clauses, dates, or values not explicitly stated.\n\n"
                f"Retrieved Evidence:\n{context_blocks}"
            )
            answer_text = self.gemini.generate_text(
                prompt=prompt,
                system_instruction="Provide grounded, concise, professional answers to MSME bidders citing tender evidence.",
            )
        else:
            # Deterministic offline synthesis: quote the highest-ranked verifiable excerpt
            top_cit = qa_citations[0]
            answer_text = (
                f"Evidence from '{top_cit.source_filename}' (Page {top_cit.page_number}):\n\n"
                f"\"{top_cit.supporting_excerpt}\"\n\n"
                f"(Deterministic evidence retrieval; remote AI synthesis is currently offline.)"
            )

        return TenderQAResponse(
            tender_id=tender.id,
            question=question,
            answer=answer_text,
            status="ANSWERED",
            confidence="HIGH" if len(qa_citations) >= 2 else "MEDIUM",
            citations=qa_citations,
        )
