import Levenshtein
import random
import rapidfuzz
import re
import uuid

# Get a random letter in lowercase
def mGetRandomLetter() -> str:
    return chr(random.randint(97, 122))

# Generate a unique id
def mGenerateId():
    return uuid.uuid4().hex

# Generate a project id
def mGenerateProjectId():
    return f'{mGetRandomLetter()}-666-{mGenerateId()}'

# Check if a string is a valid project id
def mIsProjectId(aStr: str) -> bool:
    _pattern = re.compile(r'[a-z]-666-[0-9a-f]{32}')
    return _pattern.match(aStr) is not None

# Check if value is int or string and return true type value
def mCheckIntOrStr(aValue: str) -> object:
    try:
        return int(aValue)
    except ValueError:
        return aValue

# Find the most similar string in a list
def mFindMostSimilarLeven(aStr: str, aList: list[str]) -> str:
    _mostSimilar = ''
    _maxRatio = 0
    for _str in aList:
        _ratio = Levenshtein.ratio(aStr, _str)
        if _ratio > _maxRatio:
            _maxRatio = _ratio
            _mostSimilar = _str
    return _mostSimilar

# Find list of a max number of similar strings in a list
def mListMostSimilarPartial(aStr: str, aList: list[str], aMax: int = 20) -> list[str]:
    _similarList = []
    _similarList.append(aStr)
    for _str in aList:
        _ratio = rapidfuzz.fuzz.partial_ratio(aStr, _str)
        if _ratio >= 65:
            _similarList.append(_str)
    return _similarList[:aMax]

# Find the most similar string in a list using rapidfuzz's partial_ratio
def mFindMostSimilarPartial(aStr: str, aList: list[str]) -> str:
    # Base case to improve performance
    if aStr in aList:
        return aStr
    
    # Find most similar string using partial_ratio
    _mostSimilar = ''
    _maxRatio = 0
    for _str in aList:
        _ratio = rapidfuzz.fuzz.partial_ratio(aStr, _str)
        if _ratio > _maxRatio:
            _maxRatio = _ratio
            _mostSimilar = _str
    return _mostSimilar

# Build message to show lists:
def mBuildEnlistedMessage(aTitle: str, aList: list[str], marker: str = '-', level: int = 0) -> str:
    _msg = f'{aTitle}\n'
    for _item in aList:
        _msg += f"{' ' * level}{marker} {_item}\n"
    return _msg

# Lowercase and remove any special characters or numbers
def mCleanString(aStr: str) -> str:
    return re.sub(r'[^a-zA-Z]', '', aStr).lower()