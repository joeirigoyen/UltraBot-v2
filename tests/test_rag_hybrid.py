"""
Tests for the Hybrid RAG retrieval pipeline (BM25 + Semantic + RRF).

These tests use mock data (no ChromaDB, no sentence-transformers) to verify:
1. BM25 scorer returns keyword-relevant results
2. BM25 respects blacklists
3. RRF fusion correctly merges two ranked lists
4. Edge cases (empty corpus, single perk, no BM25 matches)
"""
import sys
import os
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
_projectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _projectRoot not in sys.path:
    sys.path.insert(0, _projectRoot)

# Stub out the logger
sys.modules['log.logger'] = type(sys)('log.logger')
sys.modules['log.logger'].mLogInfo = lambda *a, **k: None
sys.modules['log.logger'].mLogError = lambda *a, **k: None

# Stub out files util
sys.modules['entities.utils.files'] = type(sys)('entities.utils.files')
sys.modules['entities.utils.files'].mGetConfigProperty = lambda *a, **k: None
sys.modules['entities.utils.files'].mGetAssetsDir = lambda *a, **k: ''

# Stub out chromadb and sentence_transformers so rag.py can import
sys.modules['chromadb'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

from entities.workers.dbd.rag import BM25Scorer, DBDRagPipeline


# ---------------------------------------------------------------------------
# Mock perk corpus
# ---------------------------------------------------------------------------
MOCK_CORPUS = {
    "Sprint Burst":    "When starting to run, break into a sprint at 150% of your normal Running Movement speed for 3 seconds. Causes the Exhausted Status Effect for 60 seconds.",
    "Dead Hard":       "When injured, tap into your adrenaline bank. Press the Active Ability button while running to dash forward. Causes the Exhausted Status Effect for 60 seconds.",
    "Lithe":           "After performing a rushed vault, break into a sprint at 150% of your normal Running Movement speed for 3 seconds. Causes the Exhausted Status Effect for 40 seconds.",
    "Iron Will":       "Your grunts of pain are reduced by 100% while injured.",
    "Kindred":         "While a Survivor is on the Hook, all Survivor auras are revealed to all other Survivors and the Killer's aura is revealed to you.",
    "Bond":            "Unlocks potential in one's aura-reading ability. The auras of all other Survivors are revealed to you when they are within 36 metres of your position.",
    "Empathy":         "Unlocks potential in one's aura-reading ability. The auras of Survivors in the Injured or Dying State are revealed to you within 128 metres.",
    "Spine Chill":     "Get a notification when the Killer is looking directly in your direction and standing within 36 metres of range.",
    "Lightweight":     "Your scratch marks disappear 3 seconds sooner than normal.",
    "Quick & Quiet":   "Your rushed actions do not trigger Loud Noise notifications and their auditory appearance range is reduced by 100%.",
    "Balanced Landing": "After falling from a height, break into a sprint at 150% of your normal Running Movement speed for 3 seconds. Causes the Exhausted Status Effect for 40 seconds.",
    "Urban Evasion":   "Your crouching Movement speed is increased by 100%.",
    "Self-Care":       "Unlocks the ability to heal yourself without a Med-Kit at 50% of the normal Healing speed.",
    "Adrenaline":      "Once the Exit Gates are powered, instantly heal one Health State and sprint at 150% of your normal Running Movement speed for 5 seconds. Causes Exhausted.",
}


# ---------------------------------------------------------------------------
# BM25 Scorer Tests
# ---------------------------------------------------------------------------

class TestBM25Scorer:

    def test_keyword_relevance(self):
        """Perks mentioning 'Exhausted' should rank when querying about exhaustion."""
        scorer = BM25Scorer(MOCK_CORPUS)
        results = scorer.rank("Exhausted sprint running speed", top_k=5)
        # Exhaustion perks should dominate the top results
        exhaustion_perks = {"Sprint Burst", "Dead Hard", "Lithe", "Balanced Landing", "Adrenaline"}
        assert len(results) > 0, "BM25 returned no results"
        top_set = set(results[:5])
        overlap = top_set & exhaustion_perks
        assert len(overlap) >= 3, (
            f"Expected at least 3 exhaustion perks in top 5, got {overlap} from {results[:5]}"
        )

    def test_aura_keyword(self):
        """Perks about aura-reading should rank for an aura query."""
        scorer = BM25Scorer(MOCK_CORPUS)
        results = scorer.rank("aura reading revealed Survivors", top_k=5)
        aura_perks = {"Bond", "Empathy", "Kindred"}
        top_set = set(results[:5])
        overlap = top_set & aura_perks
        assert len(overlap) >= 2, (
            f"Expected at least 2 aura perks in top 5, got {overlap} from {results[:5]}"
        )

    def test_blacklist_respected(self):
        """Blacklisted perks should never appear in results."""
        scorer = BM25Scorer(MOCK_CORPUS)
        blacklist = {"Sprint Burst", "Dead Hard"}
        results = scorer.rank("Exhausted sprint", blacklist=blacklist, top_k=10)
        for perk in results:
            assert perk not in blacklist, f"Blacklisted perk {perk} appeared in BM25 results"

    def test_empty_corpus(self):
        """An empty corpus should return no results."""
        scorer = BM25Scorer({})
        results = scorer.rank("anything at all")
        assert results == []

    def test_no_matching_terms(self):
        """A query with no overlapping terms should return empty."""
        scorer = BM25Scorer(MOCK_CORPUS)
        results = scorer.rank("xyzzy foobar quxquux")
        assert results == []

    def test_single_perk_corpus(self):
        """A single-perk corpus should return that perk if query matches."""
        scorer = BM25Scorer({"Iron Will": "Grunts of pain are reduced while injured."})
        results = scorer.rank("injured pain")
        assert results == ["Iron Will"]


# ---------------------------------------------------------------------------
# RRF Tests
# ---------------------------------------------------------------------------

class TestReciprocalRankFusion:

    def test_identical_lists_preserve_order(self):
        """If both lists agree, the fused order should match."""
        list_a = ["A", "B", "C", "D"]
        list_b = ["A", "B", "C", "D"]
        fused = DBDRagPipeline._reciprocal_rank_fusion([list_a, list_b])
        assert fused == ["A", "B", "C", "D"]

    def test_disjoint_lists_merge(self):
        """Items unique to each list should all appear in the output."""
        list_a = ["A", "B"]
        list_b = ["C", "D"]
        fused = DBDRagPipeline._reciprocal_rank_fusion([list_a, list_b])
        assert set(fused) == {"A", "B", "C", "D"}

    def test_shared_items_rank_higher(self):
        """A perk appearing in both lists should outrank one appearing in only one."""
        list_a = ["X", "SHARED", "Y"]
        list_b = ["Z", "SHARED", "W"]
        fused = DBDRagPipeline._reciprocal_rank_fusion([list_a, list_b])
        # SHARED has contributions from both lists, so it should be #1
        assert fused[0] == "SHARED", f"Expected SHARED at #1, got {fused[0]}"

    def test_empty_lists(self):
        """Empty inputs should produce empty output."""
        fused = DBDRagPipeline._reciprocal_rank_fusion([[], []])
        assert fused == []

    def test_single_list(self):
        """With only one list, order should be preserved."""
        fused = DBDRagPipeline._reciprocal_rank_fusion([["A", "B", "C"]])
        assert fused == ["A", "B", "C"]

    def test_k_parameter(self):
        """Using a different k should still produce valid output."""
        list_a = ["A", "B", "C"]
        list_b = ["C", "A", "B"]
        fused = DBDRagPipeline._reciprocal_rank_fusion([list_a, list_b], k=10)
        assert set(fused) == {"A", "B", "C"}
        # With k=10: A gets 1/11 + 1/12, B gets 1/12 + 1/12, C gets 1/13 + 1/11
        # A = 0.1742, C = 0.1680, B = 0.1667 -> A, C, B
        assert fused[0] == "A"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
