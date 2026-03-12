# Generic imports
import os
import random

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.files import mGetConfigProperty
from entities.utils.rare import mSuperCleanString

class PerkTracker:
    """
    Helper class to keep track of perk instances per user.

    Uses weighted random sampling to reduce repetitiveness:
    - Each perk has a weight (0.0–1.0) representing its selection probability.
    - When a perk is selected, its weight is decayed (multiplied by DECAY_FACTOR).
    - Every roll, all weights recover slightly (multiplied by RECOVERY_FACTOR, capped at 1.0).
    - Within a single build, already-picked perks are excluded (no intra-build duplicates).
    - At most MAX_EXHAUSTION_PER_BUILD exhaustion perks are allowed per build.
    - Category diversity is softly enforced by penalizing already-represented categories.
    """
    # Build constants
    BUILD_SIZE = 4
    MAX_EXHAUSTION_PER_BUILD = 1

    # Weight tuning constants
    DECAY_FACTOR = 0.1          # Selected perk drops to 10% of its current weight
    RECOVERY_FACTOR = 1.2       # All weights grow by 20% each roll
    CATEGORY_PENALTY = 0.5      # Perks sharing a category with an already-picked perk get halved weight

    # Perk dict key names
    TITLE = 'name'
    CHARACTER = 'owner_name'
    DESCRIPTION = 'main_effect'
    CATEGORIES = 'categories'
    
    def __init__(self, aUserId: str, aUserName: str, aPerks: list) -> None:
        # Set owner
        self.__userId = int(aUserId)
        self.__userName = aUserName
        self.__perks: list[dict] = aPerks
        # Initialize weights: every perk starts at full probability
        self.__weights: dict[str, float] = {
            _perk[self.TITLE]: 1.0 for _perk in self.__perks
        }
        # Build a lookup for perk metadata by name
        self.__perkLookup: dict[str, dict] = {
            _perk[self.TITLE]: _perk for _perk in self.__perks
        }
        # Roll state
        self.__lastRoll: list[str] = []
        self.__lastBuildId: int | None = None
        self.__lastMessage: str | None = None
        # Black list
        self.__blacklist: set | None = None

    def mGetWeights(self) -> dict[str, float]:
        """Return the current weights dict (for persistence)."""
        return dict(self.__weights)

    def mSetWeights(self, aWeights: dict[str, float]) -> None:
        """Merge persisted weights into the in-memory weights dict."""
        for _name, _weight in aWeights.items():
            if _name in self.__weights:
                self.__weights[_name] = _weight
        mLogInfo(f'Loaded {len(aWeights)} persisted weights for user {self.__userId}')

    # ------------------------------------------------------------------
    # Weight helpers
    # ------------------------------------------------------------------

    def _mRecoverWeights(self) -> None:
        """Gradually recover all weights toward 1.0."""
        for _name in self.__weights:
            _w = self.__weights[_name] * self.RECOVERY_FACTOR
            self.__weights[_name] = min(1.0, _w)

    def _mDecayWeight(self, aPerkId: str) -> None:
        """Reduce a perk's weight after it has been selected."""
        self.__weights[aPerkId] = self.__weights.get(aPerkId, 1.0) * self.DECAY_FACTOR
        mLogInfo(f'Weight for {aPerkId} decayed to {self.__weights[aPerkId]:.4f} for user {self.__userId}')

    def _mGetEligiblePerks(self, aExcluded: set[str], aExhaustionCount: int) -> list[dict]:
        """Return perks that are not blacklisted, not already in this build, and respect exhaustion cap."""
        _eligible = []
        for _perk in self.__perks:
            _name = _perk[self.TITLE]
            if _name in aExcluded:
                continue
            if self.__blacklist and _name in self.__blacklist:
                continue
            # Enforce exhaustion cap
            if aExhaustionCount >= self.MAX_EXHAUSTION_PER_BUILD and _perk.get('exhaustion', False):
                continue
            _eligible.append(_perk)
        return _eligible

    def _mWeightedPick(self, aExcluded: set[str], aExhaustionCount: int,
                       aUsedCategories: set[str]) -> str:
        """Pick one perk using weighted random selection from eligible perks."""
        _eligible = self._mGetEligiblePerks(aExcluded, aExhaustionCount)
        if not _eligible:
            mLogError(f'No eligible perks left for user {self.__userId}! Falling back to any non-blacklisted perk.')
            _eligible = [p for p in self.__perks
                         if p[self.TITLE] not in (self.__blacklist or set())]

        # Build weight list, applying category diversity penalty
        _weights = []
        for _perk in _eligible:
            _name = _perk[self.TITLE]
            _w = self.__weights.get(_name, 1.0)
            # Penalize perks whose categories overlap with already-picked ones
            _cats = _perk.get(self.CATEGORIES) or ''
            if aUsedCategories and _cats:
                for _cat in _cats.split(', '):
                    if _cat in aUsedCategories:
                        _w *= self.CATEGORY_PENALTY
                        break  # One penalty per perk is enough
            _weights.append(max(_w, 0.001))  # Floor to avoid zero-weight

        # Weighted random selection
        _chosen = random.choices(_eligible, weights=_weights, k=1)[0]
        _chosenName = _chosen[self.TITLE]
        mLogInfo(f'Weighted pick: {_chosenName} (w={self.__weights.get(_chosenName, 1.0):.4f}) for user {self.__userId}')
        return _chosenName

    # ------------------------------------------------------------------
    # Public API (signatures preserved for backward compatibility)
    # ------------------------------------------------------------------

    def mSetLastBuildId(self, aBuildId: int) -> None:
        self.__lastBuildId = aBuildId
        mLogInfo(f'Last build id set for user {self.__userId}: {aBuildId}')

    def mGetLastBuildId(self) -> int:
        return self.__lastBuildId

    def mUpdateLastRoll(self, aRoll: list) -> None:
        self.__lastRoll = aRoll
        mLogInfo(f'Last roll updated for user {self.__userId}. Roll: {aRoll}')

    def mGetLastRoll(self) -> list:
        return self.__lastRoll

    def mSetLastMessage(self, aMessage: str) -> None:
        self.__lastMessage = aMessage
        mLogInfo(f'Last message id set for user {self.__userId}: {aMessage}')

    def mGetLastMessage(self) -> str:
        return self.__lastMessage

    def mGetBlackList(self) -> set:
        return self.__blacklist

    def mSetBlackList(self, aBlacklist: set) -> None:
        self.__blacklist = aBlacklist

    def mIsBlacklisted(self, aPerkId: str) -> bool:
        _result = self.__blacklist is not None and aPerkId in self.__blacklist
        if _result:
            mLogInfo(f'Perk {aPerkId} is blacklisted for user {self.__userName}')
        return _result

    def mAddPerkToBlackList(self, aPerkId: str) -> None:
        if self.mIsBlacklisted(aPerkId):
            mLogError(f'Perk {aPerkId} is already blacklisted for user {self.__userName}')
            return
        self.__blacklist.add(aPerkId)

    def mRemovePerkFromBlackList(self, aPerkId: str) -> None:
        if not self.mIsBlacklisted(aPerkId):
            mLogError(f'Perk {aPerkId} is not blacklisted for user {self.__userName}')
            return
        self.__blacklist.remove(aPerkId)
        mLogInfo(f'Perk {aPerkId} removed from blacklist for user {self.__userName}')

    def mGetRandomValidPerk(self) -> str:
        """Pick a single valid perk (used by mReplacePerk / mReplacePerks)."""
        _excluded = set(self.__lastRoll) if self.__lastRoll else set()
        # Count exhaustion perks already in the current build
        _exhaustionCount = sum(
            1 for _name in self.__lastRoll
            if self.__perkLookup.get(_name, {}).get('exhaustion', False)
        )
        _usedCats = self._mCollectCategories(self.__lastRoll)
        _perkId = self._mWeightedPick(_excluded, _exhaustionCount, _usedCats)
        self._mDecayWeight(_perkId)
        mLogInfo(f'Valid replacement perk {_perkId} selected for user {self.__userId}')
        return _perkId

    def mGetRoll(self) -> list:
        """Generate a full build of BUILD_SIZE perks with weighted sampling."""
        # Recover all weights toward 1.0 before each new roll
        self._mRecoverWeights()

        _roll: list[str] = []
        _excluded: set[str] = set()
        _exhaustionCount = 0
        _usedCategories: set[str] = set()

        for _ in range(self.BUILD_SIZE):
            _perkId = self._mWeightedPick(_excluded, _exhaustionCount, _usedCategories)
            _roll.append(_perkId)
            _excluded.add(_perkId)
            # Decay the selected perk's weight
            self._mDecayWeight(_perkId)
            # Track exhaustion
            _perkData = self.__perkLookup.get(_perkId, {})
            if _perkData.get('exhaustion', False):
                _exhaustionCount += 1
            # Track categories for diversity
            _cats = _perkData.get(self.CATEGORIES) or ''
            for _cat in _cats.split(', '):
                if _cat:
                    _usedCategories.add(_cat)

        self.mUpdateLastRoll(_roll)
        return _roll

    # ------------------------------------------------------------------
    # Category helpers
    # ------------------------------------------------------------------

    def _mCollectCategories(self, aPerkNames: list[str]) -> set[str]:
        """Collect all categories from a list of perk names."""
        _cats: set[str] = set()
        for _name in aPerkNames:
            _perkData = self.__perkLookup.get(_name, {})
            _catStr = _perkData.get(self.CATEGORIES) or ''
            for _cat in _catStr.split(', '):
                if _cat:
                    _cats.add(_cat)
        return _cats

    # ------------------------------------------------------------------
    # Image / help utilities
    # ------------------------------------------------------------------

    @staticmethod
    def mGetImage(aPerkId: str) -> str:
        # Get image directory
        _imgDir = mGetConfigProperty('PERKS_IMG_DIR')
        if not _imgDir:
            mLogError("Could not retrieve property 'PERKS_IMG_DIR' from config")
            _imgDir = 'assets/dbd/imgs/perks'
            
        # Try finding the UUID from the database
        from entities.utils.sql import SQLRetriever
        try:
            _sql = SQLRetriever()
            _perk = _sql.mGetPerkByName(aPerkId)
            if _perk and _perk.get('uuid'):
                _perkName = _perk['uuid']
            else:
                _perkName = mSuperCleanString(aPerkId)
        except Exception as e:
            mLogError(f"Failed to fetch UUID for perk {aPerkId}: {e}")
            _perkName = mSuperCleanString(aPerkId)

        _imgPath = os.path.join(_imgDir, f'{_perkName}.png')
        
        # Check if perk image exists
        if not os.path.exists(_imgPath):
            _err_msg = f'Image {_imgPath} not found for perk {aPerkId}'
            mLogError(_err_msg)
            return os.path.join(_imgDir, 'notfound.png')
            
        mLogInfo(f'Image path for perk {aPerkId} retrieved: {_imgPath}')
        return _imgPath

    def mGetHelpInfo(self, aPerkId: str) -> dict:
        _perk = self.__perkLookup.get(aPerkId)
        if _perk:
            _info = {
                "owner": _perk.get('character') or "Generic",
                "categories": _perk.get(self.CATEGORIES) or "None",
                "effect": _perk.get(self.DESCRIPTION)
            }
            mLogInfo(f'Help info for perk {aPerkId} retrieved.')
            return _info
        mLogInfo(f'Help info for perk {aPerkId} not found.')
        return None

    def mGetImages(self, aPerkIds: list[str]) -> list[str]:
        _images = []
        try:
            for _perkId in aPerkIds:
                _images.append(self.mGetImage(_perkId))
            return _images
        except ValueError as e:
            mLogError(f'Error during image retrieval: {e}')
            return []

    def mGetWhitelistedPerkNames(self) -> list[str]:
        _perks = [_perk[self.TITLE] for _perk in self.__perks if not self.mIsBlacklisted(_perk['name'])]
        return _perks

    def mGetAllPerkNames(self) -> list:
        _perks = [_perk[self.TITLE] for _perk in self.__perks]
        return _perks

    def mSetLastRoll(self, aRoll: list) -> None:
        self.__lastRoll = aRoll
        mLogInfo(f'Last roll set for user {self.__userId}. Roll: {aRoll}')