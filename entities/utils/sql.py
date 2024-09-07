import pymysql as sql

from dotenv import load_dotenv
from os import getenv
from typing import Any

from entities.utils.rare import mPrepareString

class SQLRetriever:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        # SQL connection
        self.conn = sql.connect(
            host='localhost',
            user='root',
            password=getenv('SQL_PASSWORD'),
            database='ultrabotdbd'
        )
        self.__cursor = self.conn.cursor()

    # Generic retrieval method
    def mRetrieve(self, aQuery: str) -> tuple:
        self.__cursor.execute(aQuery)
        return self.__cursor.fetchall(), self.__cursor.description

    # Generic execution method
    def mExecute(self, aQuery: str) -> None:
        self.__cursor.execute(aQuery)
        self.conn.commit()

    # Get all perks
    def mGetAllPerksBasicInfo(self) -> list[dict]:
        _query = f'SELECT p.name, p.main_effect, p.is_exhaustion, u.name AS owner_name FROM perks p JOIN characters u ON p.owner_id = u.id;'
        _results, _ = self.mRetrieve(_query)
        return list({"name": _row[0], "main_effect": _row[1], "exhaustion": bool(_row[2]), "character": _row[3]} for _row in _results)

    # Get blacklist
    def mGetBlackList(self, aUserId: str) -> set:
        _query = f'SELECT p.name FROM blacklists b JOIN perks p ON b.perk_name = p.name WHERE b.user_id = {aUserId};'
        _results, _ = self.mRetrieve(_query)
        return set([_row[0] for _row in _results])

    # Update blacklist
    def mUpdateBlackList(self, aUserId: str, aBlackList: set) -> None:
        _query = f'DELETE FROM blacklists WHERE user_id = {aUserId};'
        self.mExecute(_query)
        for _perkName in aBlackList:
            _perkName = mPrepareString(_perkName)
            _query = f'INSERT INTO blacklists (user_id, perk_name) VALUES ({aUserId}, \'{_perkName}\');'
            self.mExecute(_query)

    # Register match result
    def mRegisterMatchResult(self, aParams: dict) -> None:
        # Get parameters
        _userId = aParams['userId']
        _matchResult = aParams['matchResult']
        _matchDate = aParams['matchDate']
        _perkIds = aParams['perkNames']
        # Build query
        _query = f'INSERT INTO matches (user, outcome, match_date, perk_1_name, perk_2_name, perk_3_name, perk_4_name) VALUES ('
        _query += f'{_userId}, \'{_matchResult}\', \'{_matchDate}\', '
        for _index, _perkName in enumerate(_perkIds):
            _perkName = mPrepareString(_perkName)
            if _index == 3:
                _query += f'\'{_perkName}\');'
                break
            _query += f'\'{_perkName}\', '
        # Execute query
        self.mExecute(_query)

    # Add user to database
    def mAddUser(self, aUserId: str, aUserName: str) -> None:
        _query = f'INSERT INTO users (id, name) VALUES ({aUserId}, \'{aUserName}\') ON DUPLICATE KEY UPDATE name = VALUES(name);'
        self.mExecute(_query)

    # Get all perks where there was a particular result
    def mGetMatchPerks(self, aResult: str, aUser: int = None):
        # Extract from MySQL
        _query = f"SELECT perk_1_name, perk_2_name, perk_3_name, perk_4_name FROM matches WHERE outcome = {aResult}"
        if aUser is not None:
            _query += f" AND user = {aUser}"
        _query += ";"
        # Convert to list of single
        _results, _ = self.mRetrieve(_query)
        return _results

    def mGetPerkUsage(self, aOrder: str, aUser: int, aLimit: int) -> tuple:
        # Build SQL query
        _query = "SELECT perk_name, COUNT(*) as usage_count FROM ("
        for i in range(4):
            _query += f"SELECT perk_{i + 1}_name as perk_name FROM matches"
            if aUser:
                _query += f" WHERE user = {aUser} "
            if i < 3:
                _query += " UNION ALL "
        _query += ") as perks GROUP BY perk_name"
        if aOrder == 'most':
            _query += " ORDER BY usage_count DESC"
        elif aOrder == 'least':
            _query += " ORDER BY usage_count ASC"
        _query += f" LIMIT {aLimit};"
        # Retrieve results
        _results, _description = self.mRetrieve(_query)
        _columns = [_desc[0] for _desc in _description]
        # Adjust results
        _cleanResults = [{_columns[0]: _row[0], _columns[1]: _row[1]} for _row in _results]
        return _cleanResults, _columns

    def __del__(self):
        self.conn.close()
