# Generic imports
import os
import aiohttp

# Specific imports
from discord import File, Interaction
from datetime import datetime, timedelta

# Custom imports
from log.logger import mLogInfo
from entities.utils.datahandler import DBDDataHandler
from entities.utils.files import mGetAssetsDir, mGetConfigProperty
from entities.utils.images import mCreateCollage, mSaveImage
from entities.utils.rare import mFindMostSimilarPartial
from entities.utils.sql import SQLRetriever
from entities.workers.dbd.perks import PerkTracker
from entities.workers.dbd.rag import get_rag_pipeline
import json


class DbdWorker:

    __assetsDir = mGetAssetsDir()
    __dbdAssetsDir = os.path.join(__assetsDir, 'dbd')
    __dbdGenImagesDir = mGetConfigProperty("GENERATED_IMG_DIR")

    def __init__(self, aCtx: Interaction):
        # Set owner
        self.__userId = str(aCtx.user.id)
        self.__userName = aCtx.user.name
        # Get last database update
        self.__sql = SQLRetriever()
        self.__lastDbUpdate = datetime.now()
        self.__sql.mAddUser(self.__userId, self.__userName)
        # Get blacklist from config
        self.__perks = self.mGetAllPerks()
        mLogInfo(f"Perks: {self.__perks}")
        self.__tracker = PerkTracker(self.__userId, self.__userName, self.__perks)
        self.mLoadUserBlackListFromDB()
        self.mLoadUserWeightsFromDB()
        # Load data handler
        self.__dataHandler = DBDDataHandler()
        # Log worker creation
        mLogInfo(f'Worker {self.__userId} created')

    @property
    def userId(self):
        return self.__userId
    
    @property
    def userName(self):
        return self.__userName

    def mGetAllPerks(self) -> list[dict]:
        return self.__sql.mGetAllPerksBasicInfo()

    def mGetUserBlackList(self) -> set:
        _blacklist = self.__tracker.mGetBlackList()
        if not _blacklist:
            mLogInfo(f'Blacklist not found for user {self.__userId}, loading from DB.')
            self.mLoadUserBlackListFromDB()
            _blacklist = self.__tracker.mGetBlackList()
        return _blacklist

    def mLoadUserBlackListFromDB(self) -> None:
        _blackList = self.__sql.mGetBlackList(self.__userId)
        self.__tracker.mSetBlackList(_blackList)
        mLogInfo(f'Blacklist loaded from DB for user {self.__userId}')

    def mLoadUserWeightsFromDB(self) -> None:
        _weights = self.__sql.mGetWeights(self.__userId)
        if _weights:
            self.__tracker.mSetWeights(_weights)
        mLogInfo(f'Weights loaded from DB for user {self.__userId}')

    def mSaveUserWeightsToDB(self) -> None:
        _weights = self.__tracker.mGetWeights()
        self.__sql.mSaveWeights(self.__userId, _weights)
        mLogInfo(f'Weights saved to DB for user {self.__userId}')

    def mUpdateUserBlackList(self, aForce: bool = False) -> None:
        # Check time since last update
        _maxUpdateTime = int(mGetConfigProperty('DBD_DB_UPDATE_MINS'))
        _currentTime = datetime.now()
        if not (_currentTime - self.__lastDbUpdate).min >= timedelta(_maxUpdateTime) and not aForce:
            mLogInfo(f"Skipping DB update for user {self.__userId}")
            return
        # Update blacklist and weights to DB
        self.__lastDbUpdate = _currentTime
        _currentBlackList = self.__tracker.mGetBlackList()
        self.__sql.mUpdateBlackList(self.__userId, _currentBlackList)
        self.mSaveUserWeightsToDB()
        mLogInfo(f'Blacklist and weights updated in DB for user {self.__userId}')

    def mSetLastMessage(self, aMessageId: str) -> None:
        self.__tracker.mSetLastMessage(aMessageId)

    def mGetLastMessage(self) -> str:
        return self.__tracker.mGetLastMessage()

    def mSetLastBuildId(self, aBuildId: int) -> None:
        self.__tracker.mSetLastBuildId(aBuildId)

    def mGetLastBuildId(self) -> int:
        return self.__tracker.mGetLastBuildId()

    def mGenerateCollage(self, aCtx: Interaction, aBuild: list) -> str:
        # For each perk in aBuild, get the image
        _images = self.__tracker.mGetImages(aBuild)
        # Get username
        _username = aCtx.user.name
        # Get title
        _title = f'Build for user {_username}'
        # Create and save collage
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'{_username}_randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath)
        return _imagePath

    def mGetRandomBuild(self, aCtx: Interaction) -> tuple[list[str], str]:
        # Log start of method
        mLogInfo(f'Random build requested for user {self.__userId}')
        
        # Get four random perks
        _build = self.__tracker.mGetRoll()

        # Save weights after every roll
        self.mSaveUserWeightsToDB()

        # Get collage
        _image = self.mGenerateCollage(aCtx, _build)        
        
        # Log end of method
        mLogInfo(f'Random build provided for user {self.__userId}')

        # Return build names and images
        return _build, _image

    def mGetSuggestion(self, aCtx: Interaction, aType: str) -> tuple[list[str], str]:
        # Log start
        mLogInfo(f'Suggestion requested for user {self.__userId}')

        # Get four random perks of certain type
        _build = self.__sql.mGetSuggestion(aCtx.user.id, aType)
        
        # Cache the roll so dbdhelp and other follow-ups can access it by index
        self.__tracker.mUpdateLastRoll(_build)

        # Get collage
        _image = self.mGenerateCollage(aCtx, _build)

        # Log end of method
        mLogInfo(f'Random suggestion provided for user {self.__userId}')

        # Return build names and images
        return _build, _image


    def mAddToBlackList(self, aPerkId: str) -> str:
        # Add perk to blacklist
        self.__tracker.mAddPerkToBlackList(aPerkId)

        # Log action
        _msg = f'Perk {aPerkId} added to blacklist for user {self.__userId}'
        mLogInfo(_msg)
        
        # Update to DB if needed
        self.mUpdateUserBlackList(aForce=True)
        return _msg

    def mRemoveFromBlackList(self, aPerkId: str) -> str:
        # Remove perk from blacklist
        self.__tracker.mRemovePerkFromBlackList(aPerkId)
        # Log action
        _msg = f'Perk {aPerkId} removed from blacklist for user {self.__userId}'
        mLogInfo(_msg)
        # Update to DB if needed
        self.mUpdateUserBlackList(aForce=True)
        return _msg

    def mReplacePerk(self, aCtx: Interaction, aPerkIndex: int) -> tuple[list[str], File]:
        # Get last roll
        _lastRoll = self.__tracker.mGetLastRoll()
        
        # Check if there are perks to replace
        if len(_lastRoll) < self.__tracker.BUILD_SIZE:
            raise ValueError('No perks to replace')
        
        # Get new valid perk and update last roll
        _newPerk = self.__tracker.mGetRandomValidPerk()
        _lastRoll[aPerkIndex] = _newPerk
        self.__tracker.mUpdateLastRoll(_lastRoll)
        
        # Make new collage
        _username = aCtx.user.name
        _images = self.__tracker.mGetImages(_lastRoll)
        _title = f'Build for user {_username}'
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)

        # Save collage
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath)
        _image = File(_imagePath)

        return _lastRoll, _image

    def mReplacePerks(self, aCtx: Interaction, aPerkIndices: list[int]) -> tuple[list[str], File]:
        # Get last roll
        _lastRoll = self.__tracker.mGetLastRoll()
        
        # Check if there are perks to replace
        if len(_lastRoll) < self.__tracker.BUILD_SIZE:
            raise ValueError('No perks to replace')
        
        # Get new valid perk and update last roll
        for _index in aPerkIndices:
            _newPerk = self.__tracker.mGetRandomValidPerk()
            _lastRoll[_index] = _newPerk
        self.__tracker.mUpdateLastRoll(_lastRoll)
        
        # Make new collage
        _username = aCtx.user.name
        _images = self.__tracker.mGetImages(_lastRoll)
        _title = f'Build for user {_username}'
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)

        # Save collage
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath)
        _image = File(_imagePath)

        return _lastRoll, _image

    def mGetWhitelistedPerkNames(self) -> list:
        return self.__tracker.mGetWhitelistedPerkNames()

    def mGetBlacklistedPerkNames(self) -> set:
        return self.__tracker.mGetBlackList()

    def mGetPerkNames(self) -> list:
        return self.__tracker.mGetAllPerkNames()

    def mGetHelp(self, aId: str) -> dict:
        # Get description info
        _info = self.__tracker.mGetHelpInfo(aId)
        if not _info:
            return None
            
        _description = _info["effect"].split('.')
        # Format description
        _body = ""
        for _paragraph in _description:
            if _paragraph.strip():
                _body += f"{_paragraph.strip()}.\n"

        # Return formatted dictionary
        return {
            "title": aId,
            "owner": _info["owner"],
            "categories": _info["categories"],
            "effect": _body
        }

    def mGetPerkImage(self, aPerkId: str) -> File:
        # Get image path
        _imagePath = self.__tracker.mGetImage(aPerkId)
        return File(_imagePath)

    def mGetPerkFromBuild(self, aPerkIndex: int) -> str:
        _lastRoll = self.__tracker.mGetLastRoll()
        return _lastRoll[aPerkIndex]

    def mRegisterResult(self, aWin: bool, aPerkNames: list[str]) -> None:        
        # Prepare data for DB push
        _data = {
            "userId": int(self.__userId),
            "matchResult": 'ESCAPE' if aWin else 'DEATH',
            "matchDate": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "perkNames": aPerkNames
        }
        # Register escape in user data
        self.__sql.mRegisterMatchResult(_data)
        mLogInfo(f'Registered win with perks {aPerkNames} for user {self.__userId}')

    def mSetCustomBuild(self, aCtx: Interaction, aBuild: list) -> tuple:
        # Set last roll and generate new collage
        self.__tracker.mSetLastRoll(aBuild)
        _collage = self.mGenerateCollage(aCtx, self.__tracker.mGetLastRoll())
        # Log and return
        _names = self.__tracker.mGetLastRoll()
        return _names, _collage

    def mGetUsageStats(self, aUser: str = None) -> dict:
        return self.__sql.mGetUsageStats(aUser)

    async def mGetSynergyBuild(self, aCtx: Interaction, aPerkName: str) -> tuple[list[str], File, str]:
        # Resolve the selected perk name
        _allPerks = self.mGetWhitelistedPerkNames()
        _resolvedPerk = mFindMostSimilarPartial(aPerkName, _allPerks)
        
        # Get its category/effect from help
        _helpInfo = self.mGetHelp(_resolvedPerk)
        _perkDescription = _helpInfo["effect"] if _helpInfo else "Unknown effect."
        
        # Initialize and utilize the RAG Pipeline
        _rag = get_rag_pipeline()
        
        # 1. Ensure LLM JSON and ChromaDB are initialized (fast if already exists)
        _allPerkData = self.mGetAllPerks()
        _rag.init_llm_perk_data(_allPerkData)
        _rag.init_chromadb()
        
        # 2. Retrieve top 20 similar perks, strictly omitting the user's blacklist
        _blacklist = list(self.mGetBlacklistedPerkNames())
        _similarPerkNames = _rag.retrieve_similar_perks(_perkDescription, blacklist=_blacklist, top_k=20)
        
        # Hydrate the perk names with descriptions for the LLM
        _contextStr = ""
        for _pName in _similarPerkNames:
            if _pName == _resolvedPerk: continue # Don't provide target perk as suggestion
            _hInfo = self.mGetHelp(_pName)
            _desc = _hInfo["effect"] if _hInfo else ""
            _contextStr += f"- {_pName}: {_desc}\n"

        # Compile JSON-enforced prompt
        _prompt = (
            f"You are an expert at Dead by Daylight survivor builds. "
            f"Your task is to craft a highly synergistic and optimal 4-perk build centered around the perk '{_resolvedPerk}'.\n"
            f"The effect of '{_resolvedPerk}' is: '{_perkDescription}'.\n\n"
            f"You MUST choose exactly 3 other perks from the following list of mechanically similar possibilities:\n"
            f"{_contextStr}\n"
            f"Do NOT include '{_resolvedPerk}' in the 3 suggestions.\n"
            f"Your response MUST be exclusively a valid JSON object matching this exact schema, and nothing else:\n"
            f"{{\n"
            f"  \"build_name\": \"A catchy name for the build\",\n"
            f"  \"perks\": [\"Perk 1\", \"Perk 2\", \"Perk 3\", \"Perk 4\"],\n"
            f"  \"strategy\": \"A brief, 2-3 sentence explanation of how the build works and how to play it for maximum advantage.\"\n"
            f"}}\n"
            f"Ensure the list \"perks\" contains exactly 4 strings, including '{_resolvedPerk}'."
        )
        
        _ollamaUrl = mGetConfigProperty("OLLAMA_URL") or "http://localhost:11434/api/generate"
        _ollamaModel = mGetConfigProperty("OLLAMA_MODEL") or "llama3.1"
        
        mLogInfo(f"Requesting synergy build from Ollama for perk '{_resolvedPerk}' via JSON RAG...")
        async with aiohttp.ClientSession() as session:
            async with session.post(_ollamaUrl, json={
                "model": _ollamaModel,
                "prompt": _prompt,
                "stream": False,
                "format": "json"    # Enforce JSON output via Ollama API
            }) as response:
                if response.status != 200:
                    raise Exception(f"Ollama API returned status {response.status}")
                _data = await response.json()
                _responseStr = _data.get("response", "")
                
        # Parse the JSON response
        _suggestedPerks = []
        _explanation = "No explanation provided."
        _buildName = ""
        try:
            _jsonResp = json.loads(_responseStr)
            _suggestedPerks = _jsonResp.get("perks", [])
            _explanation = _jsonResp.get("strategy", _explanation)
            _buildName = _jsonResp.get("build_name", "")
            if _buildName:
                _explanation = f"**{_buildName}**\n\n" + _explanation
        except json.JSONDecodeError as e:
            mLogError(f"Failed to decode Ollama JSON response: {e}\nRaw: {_responseStr}")

        # Validate perks against whitelist
        _finalBuild = [_resolvedPerk]
        for p in _suggestedPerks:
            if not isinstance(p, str) or not p: continue
            _matched = mFindMostSimilarPartial(p, _allPerks)
            if _matched and _matched not in _finalBuild and len(_finalBuild) < self.__tracker.BUILD_SIZE:
                _finalBuild.append(_matched)
                
        # Fallback: Fill the rest with random valid perks if the LLM hallucinated heavily or returned < 4 valid
        while len(_finalBuild) < self.__tracker.BUILD_SIZE:
            mLogInfo("LLM provided invalid/blacklisted perks. Falling back to random whitelisted perk.")
            _newPerk = self.__tracker.mGetRandomValidPerk()
            if _newPerk not in _finalBuild:
                _finalBuild.append(_newPerk)
                
        # Set current build to this synergy build
        self.__tracker.mUpdateLastRoll(_finalBuild)
        
        # Generate collage
        _imagePath = self.mGenerateCollage(aCtx, _finalBuild)
        from discord import File
        _image = File(_imagePath)
        
        return _finalBuild, _image, _explanation

    def mKillSQLRetriever(self) -> None:
        del self.__sql
        mLogInfo("Closed SQL connection")
