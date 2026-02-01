"""
CLI script for ingesting data from various sources
Supports: JSONL, TXT, MD, DOCX, PDF, JPEG, PNG

Usage:
    python scripts/ingest_logs.py --source data/raw/logs.jsonl
    python scripts/ingest_logs.py --source data/raw/report.pdf --source-type docs
    python scripts/ingest_logs.py --source data/raw/chart.png --source-type image
"""
import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.layer1_ingestion.loaders import load_jsonl_logs
from src.layer1_ingestion.normalizers import (
    normalize_bot_log,
    normalize_eia_data,
    normalize_news_item,
)
from src.layer1_ingestion.deduplication import deduplicate_events, validate_event_integrity
from src.layer2_storage.vector_store import VectorStore
from src.layer2_storage.metadata_store import MetadataStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UniversalIngestion:
    """Universal data ingestion pipeline supporting multiple formats"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.metadata_store = MetadataStore()
        
        # Try to load existing index
        try:
            self.vector_store.load()
            logger.info("Loaded existing vector index")
        except Exception as e:
            logger.info("Starting with empty vector index")
    
    async def ingest_file(
        self,
        file_path: Path,
        source_type: str = "auto"
    ):
        """
        Ingest single file
        
        Args:
            file_path: Path to file
            source_type: Type of source data
                - 'auto': Auto-detect from extension
                - 'logs': Trading bot logs (JSONL)
                - 'eia': EIA reports (PDF/TXT)
                - 'news': News articles (TXT/MD)
                - 'docs': Generic documents (DOCX/PDF)
                - 'image': Images/charts (JPEG/PNG)
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        # Auto-detect source type from extension
        if source_type == "auto":
            source_type = self._detect_source_type(file_path)
        
        logger.info(f"Ingesting {file_path} as type '{source_type}'")
        
        # Route to appropriate parser
        if source_type == "logs":
            await self._ingest_jsonl_logs(file_path)
        elif source_type == "eia":
            await self._ingest_eia_document(file_path)
        elif source_type == "news":
            await self._ingest_news_document(file_path)
        elif source_type == "docs":
            await self._ingest_generic_document(file_path)
        elif source_type == "image":
            await self._ingest_image(file_path)
        else:
            logger.error(f"Unknown source type: {source_type}")
    
    def _detect_source_type(self, file_path: Path) -> str:
        """Auto-detect source type from file extension"""
        ext = file_path.suffix.lower()
        
        if ext == ".jsonl":
            return "logs"
        elif ext == ".pdf" and "eia" in file_path.name.lower():
            return "eia"
        elif ext in [".txt", ".md"]:
            return "news"
        elif ext in [".docx", ".pdf"]:
            return "docs"
        elif ext in [".jpg", ".jpeg", ".png"]:
            return "image"
        else:
            logger.warning(f"Unknown extension {ext}, defaulting to 'docs'")
            return "docs"
    
    async def _ingest_jsonl_logs(self, file_path: Path):
        """Ingest JSONL trading bot logs"""
        logger.info("Loading JSONL logs...")
        
        # Load raw logs
        raw_logs = await load_jsonl_logs(file_path)
        
        if not raw_logs:
            logger.warning("No logs found in file")
            return
        
        # Normalize to IngestedEvent
        events = []
        for raw_log in raw_logs:
            try:
                event = normalize_bot_log(raw_log)
                if validate_event_integrity(event):
                    events.append(event)
            except Exception as e:
                logger.warning(f"Failed to normalize log: {e}")
                continue
        
        logger.info(f"Normalized {len(events)} events from {len(raw_logs)} logs")
        
        # Deduplicate
        events, stats = deduplicate_events(events)
        logger.info(f"Deduplication: {stats}")
        
        # Store in Layer 2
        await self._store_events(events)
    
    async def _ingest_eia_document(self, file_path: Path):
        """Ingest EIA report (PDF/TXT)"""
        logger.info("Ingesting EIA document...")
        
        # Extract text from PDF/TXT
        text = await self._extract_text(file_path)
        
        if not text:
            logger.warning("No text extracted from document")
            return
        
        # Create generic document event
        from src.layer1_ingestion.models import IngestedEvent
        from datetime import datetime, timezone
        
        event = IngestedEvent(
            event_id="",  # Auto-generated
            source="eia",
            canonical_form={
                "filename": file_path.name,
                "text_length": len(text),
                "preview": text[:500],
            },
            embedding_text=f"EIA document: {file_path.name}. Content: {text[:1000]}",
            metadata={
                "authority": 1.0,  # EIA = highest authority
                "freshness": datetime.now(timezone.utc),
                "data_period": None,
            }
        )
        
        await self._store_events([event])
    
    async def _ingest_news_document(self, file_path: Path):
        """Ingest news article (TXT/MD)"""
        logger.info("Ingesting news document...")
        
        text = await self._extract_text(file_path)
        
        if not text:
            return
        
        from src.layer1_ingestion.models import IngestedEvent
        from src.layer1_ingestion.normalizers import _calculate_simple_sentiment
        from datetime import datetime, timezone
        
        sentiment = _calculate_simple_sentiment(text)
        
        event = IngestedEvent(
            event_id="",
            source="news",
            canonical_form={
                "filename": file_path.name,
                "text": text,
                "sentiment_score": sentiment,
            },
            embedding_text=f"News article: {file_path.name}. Content: {text[:1000]}",
            metadata={
                "authority": 0.6,  # News = medium authority
                "freshness": datetime.now(timezone.utc),
                "data_period": None,
            }
        )
        
        await self._store_events([event])
    
    async def _ingest_generic_document(self, file_path: Path):
        """Ingest generic document (DOCX/PDF)"""
        logger.info("Ingesting generic document...")
        
        text = await self._extract_text(file_path)
        
        if not text:
            return
        
        from src.layer1_ingestion.models import IngestedEvent
        from datetime import datetime, timezone
        
        event = IngestedEvent(
            event_id="",
            source="docs",
            canonical_form={
                "filename": file_path.name,
                "text": text,
            },
            embedding_text=f"Document: {file_path.name}. Content: {text[:1000]}",
            metadata={
                "authority": 0.7,
                "freshness": datetime.now(timezone.utc),
                "data_period": None,
            }
        )
        
        await self._store_events([event])
    
    async def _ingest_image(self, file_path: Path):
        """Ingest image (JPEG/PNG) - OCR or placeholder for Phase 2"""
        logger.info("Ingesting image (OCR not implemented yet, storing metadata only)...")
        
        from src.layer1_ingestion.models import IngestedEvent
        from datetime import datetime, timezone
        from PIL import Image
        
        try:
            img = Image.open(file_path)
            width, height = img.size
            
            event = IngestedEvent(
                event_id="",
                source="image",
                canonical_form={
                    "filename": file_path.name,
                    "width": width,
                    "height": height,
                    "format": img.format,
                },
                embedding_text=f"Image file: {file_path.name} ({width}x{height})",
                metadata={
                    "authority": 0.5,
                    "freshness": datetime.now(timezone.utc),
                    "data_period": None,
                }
            )
            
            await self._store_events([event])
            
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
    
    async def _extract_text(self, file_path: Path) -> str:
        """Extract text from various formats"""
        ext = file_path.suffix.lower()

        if ext in [".txt", ".md", ".jsonl"]:
            # Plain text
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        elif ext == ".pdf":
            # PDF extraction (requires PyPDF2)
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        page_text = page.extract_text() or ""
                        text += page_text
                return text
            except ImportError:
                logger.error("PyPDF2 not installed. Install: pip install PyPDF2")
                return ""

        elif ext == ".docx":
            # DOCX extraction (requires python-docx)
            try:
                from docx import Document
                doc = Document(str(file_path))  # FIX: Path -> str for type checker
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                logger.error("python-docx not installed. Install: pip install python-docx")
                return ""

        else:
            logger.warning(f"Text extraction not implemented for {ext}")
            return ""

    
    async def _store_events(self, events: List):
        """Store events in Layer 2 (VectorStore + MetadataStore)"""
        if not events:
            logger.warning("No events to store")
            return
        
        # Extract data for vector store
        event_ids = [e.event_id for e in events]
        texts = [e.embedding_text for e in events]
        
        # Add to vector store
        self.vector_store.add_events(event_ids, texts)
        
        # Add to metadata store
        self.metadata_store.bulk_insert_events(events)
        
        logger.info(f"Stored {len(events)} events")
        
        # Save vector index to disk
        self.vector_store.save()
        logger.info("Saved vector index to disk")


async def main():
    parser = argparse.ArgumentParser(
        description="Universal data ingestion for DAG system"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to source file or directory"
    )
    parser.add_argument(
        "--source-type",
        type=str,
        default="auto",
        choices=["auto", "logs", "eia", "news", "docs", "image"],
        help="Type of source data (default: auto-detect)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process directory recursively"
    )
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    ingestion = UniversalIngestion()
    
    if source_path.is_file():
        # Single file
        await ingestion.ingest_file(source_path, args.source_type)
    
    elif source_path.is_dir():
        # Directory
        pattern = "**/*" if args.recursive else "*"
        files = [f for f in source_path.glob(pattern) if f.is_file()]
        
        logger.info(f"Found {len(files)} files in {source_path}")
        
        for file in files:
            try:
                await ingestion.ingest_file(file, args.source_type)
            except Exception as e:
                logger.error(f"Failed to ingest {file}: {e}")
                continue
    
    else:
        logger.error(f"Source not found: {source_path}")
        sys.exit(1)
    
    logger.info("✅ Ingestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
