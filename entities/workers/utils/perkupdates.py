# General imports
import requests

# Specific imports
from bs4 import BeautifulSoup, Tag, NavigableString, ResultSet
from enum import Enum
from tenacity import retry, wait_exponential, stop_after_attempt

# Custom imports
from entities.utils.files import mGetDBDConfig
from log.logger import mLogInfo, mLogError

class Perk(Enum):
    """
    Enum to represent the columns of the perk data.
    """
    ID = "id"
    NAME = "name"
    CHARACTER = "character"
    CATEGORY = "category"
    MAINEFFECT = "main_effect"
    SECONDARYEFFECT = "secondary_effect"
    ADDITIONALEFFECT = "additional_effect"
    QUOTE = "quote"
    IMAGE = "image"

class PerkData:
    """
    Class to represent perk data as a dictionary once it has been parsed.
    """
    __forcefulKeys = [_value for _, _value in Perk.__members__.items()]

    def __init__(self, aDict: dict[str, str]):
        self.__dict = self.mValidateDict(aDict)

    @property
    def id(self) -> str:
        return self.__dict[Perk.ID.value]
    
    @property
    def name(self) -> str:
        return self.__dict[Perk.NAME.value]
    
    @property
    def character(self) -> str:
        return self.__dict[Perk.CHARACTER.value]
    
    @property
    def category(self) -> str:
        return self.__dict[Perk.CATEGORY.value]
    
    @property
    def main_effect(self) -> str:
        return self.__dict[Perk.MAINEFFECT.value]
    
    @property
    def secondary_effect(self) -> str:
        return self.__dict[Perk.SECONDARYEFFECT.value]
    
    @property
    def additional_effect(self) -> str:
        return self.__dict[Perk.ADDITIONALEFFECT.value]
    
    @property
    def quote(self) -> str:
        return self.__dict[Perk.QUOTE.value]
    
    @property
    def image(self) -> str:
        return self.__dict[Perk.IMAGE.value]
    
    def mWriteToCSV(self, aPath: str) -> None:
        """
        Method to write the perk data to a CSV file.
        """
        try:
            with open(aPath, "w+") as _file:
                _file.write(f"{self.id},{self.name},{self.character},{self.category},{self.main_effect},{self.secondary_effect},{self.additional_effect},{self.quote},{self.image}\n")
        except Exception as _e:
            mLogError(f"Error writing to CSV: {_e}")

    def mValidateDict(self, aDict: dict[str, str]) -> dict[str, str]:
        """
        Method to validate the dictionary of perk data.
        """
        for _key in self.__forcefulKeys:
            if _key not in aDict:
                raise ValueError(f"Key {_key} not found in dictionary.")
        return aDict
    

class WebRetriever:
    """
    Class to retrieve data from the web and parse it into valid perk data.
    """
    def __init__(self, aURL):
        self.__url = aURL
        self.__response: requests.models.Response = self.mFetchResponse(self.__url)
        self.__soup: BeautifulSoup = BeautifulSoup(self.__response.content, "html.parser")

    # Retry mechanism for network requests
    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(5))
    def mFetchResponse(self, aURL: str) -> requests.models.Response:
        _response = requests.get(aURL)
        _response.raise_for_status() # Raise an exception for HTTP errors
        return _response

    def mGetTable(self, aName: str) -> Tag | NavigableString | None:
        """
        Method to get the table of perk data from the web.
        """
        try:
            _table = self.__soup.find("table", {"class": aName})
            if not _table:
                mLogInfo(f"No matching table found for class: {aName}")
                return None
            return _table
        except Exception as _e:
            mLogError(f"Error getting table: {_e}")
            return None

    def mGetTableHeader(self, aTable: Tag | NavigableString) -> list[str]:
        """
        Method to get the header of the table.
        """
        try:
            _header = aTable.find("thead").find("tr")
            if not _header:
                mLogInfo("No header found in table.")
                return []
            return [str(_th.get_text(strip=True)) for _th in _header.find_all("th")]
        except Exception as _e:
            mLogError(f"Error getting table header: {_e}")
            return []

    def mGetTableRows(self, aTable: Tag | NavigableString) -> list[Tag | NavigableString]:
        """
        Method to get the rows of the table.
        """
        try:
            # Get body and rows
            _body = aTable.find("tbody")
            _rows = _body.find_all("tr")
            # Check if rows exist
            if not _rows:
                mLogInfo("No rows found in table.")
                return []
            return _rows
        except Exception as _e:
            mLogError(f"Error getting table rows: {_e}")
            return []

    def mGetRowsData(self, aHeader: list[str], aRows: list[Tag | NavigableString]) -> list[dict[str, str]]:
        """
        Method to get the data from the rows of the table.
        """
        try:
            for _row in aRows:
                # Get ths
                _ths: ResultSet[Tag] = _row.find_all("th")
                # Get a href tags
                _iconObj: Tag = _ths[0]
                _nameObj: Tag = _ths[1]
                _charObj: Tag = _ths[2]
                # Extract data from a href tags
                _iconSrc: str = _iconObj.get("href")
                _name: str = _nameObj.get("title")
                _char: str = _charObj.get("title")
                # Get tds
                _tds: ResultSet[Tag | NavigableString] = _row.find_all("td")
                # Get p tags
                _descObj: Tag = _tds[0]
                _pTags: ResultSet[Tag] = _descObj.find_all("p")
                _ulTags: ResultSet[Tag] = _descObj.find_all("ul")
                # Extract data from p tags
                _mainEffect: str = _pTags[0].get_text(strip=True)
                _secondaryEffect: str = _pTags[1].get_text(strip=True)
                _quote: str = _pTags[2].get_text(strip=True)
                

        except Exception as _e:
            mLogError(f"Error getting rows data: {_e}")
            return []

if __name__ == '__main__':
    _perkData = PerkData({
        Perk.ID.value: "1",
        Perk.NAME.value: "Test",
        Perk.CHARACTER.value: "Test",
        Perk.CATEGORY.value: "Test",
        Perk.MAINEFFECT.value: "Test",
        Perk.SECONDARYEFFECT.value: "Test",
        Perk.ADDITIONALEFFECT.value: "Test",
        Perk.QUOTE.value: "Test",
        Perk.IMAGE.value: "Test"
    })
