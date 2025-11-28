"""
Verse Service - Handles all Quran verse operations
Integrates batch queries, caching, and validation
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from google.cloud import firestore
import redis

from ..models.verse_models import (
    VerseReference, VerseData, VerseRange,
    CrossReference, VerseWithMetadata
)
from ..models.tafsir_models import TafsirResponse
from .batch_query_service import BatchQueryService
from .cache_service import CacheService
from ..config.settings import settings, QURAN_METADATA

logger = logging.getLogger(__name__)


class VerseService:
    """Service for all verse-related operations"""

    def __init__(self, db: firestore.Client, redis_client: redis.Redis):
        """
        Initialize verse service

        Args:
            db: Firestore database client
            redis_client: Redis client
        """
        self.db = db
        self.batch_service = BatchQueryService(db)
        self.cache_service = CacheService(redis_client, db)

        # In-memory caches (loaded on startup)
        self.tafsir_chunks = {}
        self.verse_metadata = {}
        self.common_verses_cache = {}

        # Prefetch common verses if enabled
        if settings.enable_verse_prefetch:
            self._prefetch_common_verses()

    def _prefetch_common_verses(self):
        """Prefetch commonly referenced verses on startup"""
        try:
            logger.info("Prefetching common verses...")
            self.common_verses_cache = self.batch_service.prefetch_common_verses()
            logger.info(f"Prefetched {len(self.common_verses_cache)} common verses")
        except Exception as e:
            logger.error(f"Failed to prefetch common verses: {e}")

    def get_verse(self, surah: int, verse: int) -> Optional[VerseData]:
        """
        Get a single verse with caching

        Args:
            surah: Surah number
            verse: Verse number

        Returns:
            VerseData or None if not found
        """
        # Check common verses cache first
        cache_key = f"{surah}:{verse}"
        if cache_key in self.common_verses_cache:
            verse_dict = self.common_verses_cache[cache_key]
            return VerseData(**verse_dict)

        # Fetch using batch service (even for single verse for consistency)
        verses = self.batch_service.batch_get_verses([(surah, verse)])

        if cache_key in verses:
            verse_dict = verses[cache_key]
            return VerseData(
                surah_number=verse_dict['surah_number'],
                verse_number=verse_dict['verse_number'],
                arabic_text=verse_dict.get('arabic', ''),
                english_text=verse_dict.get('en_sahih', ''),
                transliteration=verse_dict.get('en_transliteration')
            )

        logger.warning(f"Verse {surah}:{verse} not found")
        return None

    def get_verses_batch(self, verse_refs: List[Tuple[int, int]]) -> List[VerseData]:
        """
        Get multiple verses efficiently using batch queries

        Args:
            verse_refs: List of (surah, verse) tuples

        Returns:
            List of VerseData objects
        """
        if not verse_refs:
            return []

        # Use batch service for efficient fetching
        verses_dict = self.batch_service.batch_get_verses(verse_refs)

        # Convert to VerseData objects
        verse_objects = []
        for (surah, verse) in verse_refs:
            key = f"{surah}:{verse}"
            if key in verses_dict:
                verse_dict = verses_dict[key]
                verse_objects.append(VerseData(
                    surah_number=verse_dict['surah_number'],
                    verse_number=verse_dict['verse_number'],
                    arabic_text=verse_dict.get('arabic', ''),
                    english_text=verse_dict.get('en_sahih', ''),
                    transliteration=verse_dict.get('en_transliteration')
                ))

        logger.info(f"Fetched {len(verse_objects)}/{len(verse_refs)} verses in batch")
        return verse_objects

    def get_verse_range(self, surah: int, start_verse: int, end_verse: int) -> List[VerseData]:
        """
        Get a range of verses efficiently

        Args:
            surah: Surah number
            start_verse: Starting verse
            end_verse: Ending verse

        Returns:
            List of VerseData objects
        """
        # Validate range
        verse_range = VerseRange(surah=surah, start_verse=start_verse, end_verse=end_verse)

        # Use batch service for range fetching
        verses_list = self.batch_service.batch_get_verse_range(
            verse_range.surah,
            verse_range.start_verse,
            verse_range.end_verse
        )

        # Convert to VerseData objects
        return [
            VerseData(
                surah_number=v['surah_number'],
                verse_number=v['verse_number'],
                arabic_text=v.get('arabic', ''),
                english_text=v.get('en_sahih', ''),
                transliteration=v.get('en_transliteration')
            )
            for v in verses_list
        ]

    def extract_and_fetch_verse_references(self, text: str) -> List[VerseData]:
        """
        Extract verse references from text and fetch them

        Args:
            text: Text containing verse references

        Returns:
            List of VerseData for found references
        """
        # Extract references using regex
        verse_refs = self._extract_verse_references(text)

        if not verse_refs:
            return []

        # Parse references to tuples
        parsed_refs = []
        for ref in verse_refs:
            try:
                verse_ref = VerseReference.from_string(ref)
                parsed_refs.append((verse_ref.surah, verse_ref.verse))
            except ValueError:
                logger.warning(f"Invalid verse reference: {ref}")
                continue

        # Batch fetch all references
        return self.get_verses_batch(parsed_refs)

    def _extract_verse_references(self, text: str) -> List[str]:
        """
        Extract verse references from text

        Args:
            text: Text to search

        Returns:
            List of verse reference strings
        """
        references = []

        # Pattern 1: Direct references like "31:12" or "(31:12)"
        pattern1 = r'\b(\d{1,3}):(\d{1,3})\b'
        matches1 = re.findall(pattern1, text)
        for surah, verse in matches1:
            references.append(f"{surah}:{verse}")

        # Pattern 2: Named references like "Surah Luqman 31:12"
        pattern2 = r'(?:Surah\s+)?(?:Al-)?[A-Za-z-]+\s+(\d{1,3}):(\d{1,3})'
        matches2 = re.findall(pattern2, text)
        for surah, verse in matches2:
            references.append(f"{surah}:{verse}")

        # Remove duplicates while preserving order
        seen = set()
        unique_refs = []
        for ref in references:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        return unique_refs

    def get_cross_references(self, verse_ref: str) -> List[CrossReference]:
        """
        Get cross-references for a verse with their Arabic text

        Args:
            verse_ref: Verse reference string (e.g., "2:255")

        Returns:
            List of CrossReference objects with Arabic text
        """
        # This would normally query a cross-reference database
        # For now, using a simplified implementation
        cross_refs = []

        # Common cross-references (would be from database)
        common_cross_refs = {
            "2:255": ["2:256", "3:2", "20:111"],
            "39:53": ["25:70", "42:25", "11:90"],
            "2:186": ["50:16", "57:4", "11:61"],
            # Add more mappings
        }

        ref_list = common_cross_refs.get(verse_ref, [])

        if ref_list:
            # Parse and fetch all cross-references in batch
            parsed_refs = []
            for ref in ref_list:
                try:
                    vr = VerseReference.from_string(ref)
                    parsed_refs.append((vr.surah, vr.verse))
                except ValueError:
                    continue

            # Batch fetch
            verses = self.get_verses_batch(parsed_refs)

            # Create CrossReference objects
            for verse in verses:
                cross_refs.append(CrossReference(
                    verse=verse.reference,
                    arabic_text=verse.arabic_text,
                    english_text=verse.english_text,
                    relevance="Related verse for deeper understanding"
                ))

        return cross_refs

    def enrich_response_with_arabic(self, response: Dict) -> Dict:
        """
        Ensure all referenced verses in a response have Arabic text

        Args:
            response: Response dictionary from Gemini

        Returns:
            Enriched response with all Arabic texts
        """
        # Extract all verse references from tafsir explanations
        all_refs = set()

        # Get references from main verses
        for verse in response.get('verses', []):
            if 'surah_number' in verse and 'verse_number' in verse:
                all_refs.add((verse['surah_number'], verse['verse_number']))

        # Extract from tafsir explanations
        for explanation in response.get('tafsir_explanations', []):
            text = explanation.get('explanation', '')
            extracted = self._extract_verse_references(text)
            for ref in extracted:
                try:
                    vr = VerseReference.from_string(ref)
                    all_refs.add((vr.surah, vr.verse))
                except ValueError:
                    continue

        # Batch fetch all verses
        if all_refs:
            verses_dict = self.batch_service.batch_get_verses(list(all_refs))

            # Add supplementary verses
            supplementary = []
            main_refs = {f"{v.get('surah_number')}:{v.get('verse_number')}"
                        for v in response.get('verses', [])}

            for ref_tuple in all_refs:
                ref_str = f"{ref_tuple[0]}:{ref_tuple[1]}"
                if ref_str not in main_refs and ref_str in verses_dict:
                    verse_data = verses_dict[ref_str]
                    supplementary.append({
                        'surah_number': verse_data['surah_number'],
                        'verse_number': verse_data['verse_number'],
                        'arabic_text': verse_data.get('arabic', ''),
                        'english_text': verse_data.get('en_sahih', ''),
                        'is_supplementary': True
                    })

            if supplementary:
                response['supplementary_verses'] = supplementary

        return response

    def validate_verse_reference(self, ref: str) -> bool:
        """
        Validate if a verse reference exists

        Args:
            ref: Verse reference string (e.g., "2:255")

        Returns:
            True if valid, False otherwise
        """
        try:
            verse_ref = VerseReference.from_string(ref)

            # Check against known Quran structure
            if verse_ref.surah not in QURAN_METADATA:
                return False

            surah_info = QURAN_METADATA[verse_ref.surah]
            if verse_ref.verse > surah_info['verses']:
                return False

            return True

        except (ValueError, KeyError):
            return False

    def cleanup(self):
        """Clean up resources"""
        self.batch_service.cleanup()