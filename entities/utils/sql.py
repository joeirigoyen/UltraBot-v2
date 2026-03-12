import pymysql as sql

from dotenv import load_dotenv
from os import getenv
from typing import Any, Literal

from entities.utils.rare import mPrepareString
from log.logger import mLogError


class SQLRetriever:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        # SQL connection
        self.conn = sql.connect(
            host='localhost',
            user='root',
            password=getenv('SQL_PASSWORD'),
            database='ultrabotdbd',
            autocommit=True
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
        _query = """
            SELECT p.name, p.main_effect, p.is_exhaustion, u.name AS owner_name, GROUP_CONCAT(t.type SEPARATOR ', ') AS categories
            FROM perks p
            LEFT JOIN characters u ON p.owner_id = u.id
            LEFT JOIN perk_types pt ON p.id = pt.perk_id
            LEFT JOIN types t ON pt.type_id = t.id
            GROUP BY p.id;
        """
        _results, _ = self.mRetrieve(_query)
        return list({"name": _row[0], "main_effect": _row[1], "exhaustion": bool(_row[2]), "character": _row[3], "categories": _row[4]} for _row in _results)

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

    # Get perk weights for a user (only decayed weights are stored)
    def mGetWeights(self, aUserId: str) -> dict[str, float]:
        _query = f'SELECT perk_name, weight FROM perk_weights WHERE user_id = {aUserId};'
        _results, _ = self.mRetrieve(_query)
        return {_row[0]: float(_row[1]) for _row in _results}

    # Save perk weights for a user (delete-and-reinsert, only weights < 1.0)
    def mSaveWeights(self, aUserId: str, aWeights: dict[str, float]) -> None:
        _query = f'DELETE FROM perk_weights WHERE user_id = {aUserId};'
        self.mExecute(_query)
        for _perkName, _weight in aWeights.items():
            if _weight < 1.0:
                _safeName = mPrepareString(_perkName)
                _query = f'INSERT INTO perk_weights (user_id, perk_name, weight) VALUES ({aUserId}, \'{_safeName}\', {_weight});'
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

    # Get character id by name
    def mGetCharacterId(self, aName: str) -> int:
        _name = mPrepareString(aName)
        _query = f"SELECT id FROM characters WHERE name = '{_name}';"
        _results, _ = self.mRetrieve(_query)
        if _results:
            return _results[0][0]
        return None

    # Insert character and return new id
    def mInsertCharacter(self, aName: str) -> int:
        _name = mPrepareString(aName)
        _query = f"INSERT INTO characters (name, gender) VALUES ('{_name}', 'U');"
        self.mExecute(_query)
        _results, _ = self.mRetrieve("SELECT LAST_INSERT_ID();")
        return _results[0][0]

    # Get perk by name
    def mGetPerkByName(self, aName: str) -> dict:
        _name = mPrepareString(aName)
        _query = f"SELECT id, uuid FROM perks WHERE name = '{_name}';"
        _results, _ = self.mRetrieve(_query)
        if _results:
            return {"id": _results[0][0], "uuid": _results[0][1]}
        return None

    # Update perk
    def mUpdatePerk(self, aId: int, aUuid: str, aOwnerId: int, aMainEffect: str, aIsExhaustion: bool) -> None:
        _mainEffect = mPrepareString(aMainEffect)
        _ownerIdSql = "NULL" if aOwnerId is None else str(aOwnerId)
        _isExhausSql = "1" if aIsExhaustion else "0"
        _query = f"UPDATE perks SET uuid = '{aUuid}', owner_id = {_ownerIdSql}, main_effect = '{_mainEffect}', is_exhaustion = {_isExhausSql} WHERE id = {aId};"
        self.mExecute(_query)

    # Insert perk
    def mInsertPerk(self, aUuid: str, aName: str, aOwnerId: int, aMainEffect: str, aIsExhaustion: bool) -> None:
        _name = mPrepareString(aName)
        _mainEffect = mPrepareString(aMainEffect)
        _ownerIdSql = "NULL" if aOwnerId is None else str(aOwnerId)
        _isExhausSql = "1" if aIsExhaustion else "0"
        _query = f"INSERT INTO perks (uuid, name, owner_id, main_effect, is_exhaustion) VALUES ('{aUuid}', '{_name}', {_ownerIdSql}, '{_mainEffect}', {_isExhausSql});"
        self.mExecute(_query)

    # Get all perks where there was a particular result
    def mGetMatchPerks(self, aResult: str, aUser: int = None) -> tuple:
        # Extract from MySQL
        _query = f"SELECT perk_1_name, perk_2_name, perk_3_name, perk_4_name FROM matches WHERE outcome = {aResult}"
        if aUser is not None:
            _query += f" AND user = {aUser}"
        _query += ";"
        # Convert to list of single
        _results, _ = self.mRetrieve(_query)
        return _results

    def mGetUsageStats(self, aUser: str = None) -> dict:
        _results = {
            "total_matches": 0,
            "wins": 0,
            "losses": 0,
            "top_perks": [],
            "worst_perks": []
        }
        
        _userFilter = ""
        if aUser:
            _userFilter = f"WHERE user = (SELECT id FROM users WHERE name = '{aUser}')"
            _perksUserFilter = f"WHERE user = (SELECT id FROM users WHERE name = '{aUser}') AND perk_name IS NOT NULL"
        else:
            _perksUserFilter = "WHERE perk_name IS NOT NULL"

        # Overall matches
        _queryMatches = f"SELECT outcome, COUNT(*) FROM matches {_userFilter} GROUP BY outcome;"
        _matchRows, _ = self.mRetrieve(_queryMatches)
        for _outcome, _count in _matchRows:
            if _outcome == 'ESCAPE':
                _results["wins"] += _count
            elif _outcome == 'DEATH':
                _results["losses"] += _count
        _results["total_matches"] = _results["wins"] + _results["losses"]

        # Perks stats
        _queryPerks = f"""
            SELECT perk_name, 
                   SUM(CASE WHEN outcome = 'ESCAPE' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN outcome = 'DEATH' THEN 1 ELSE 0 END) as losses
            FROM (
                SELECT perk_1_name as perk_name, outcome, user FROM matches
                UNION ALL
                SELECT perk_2_name as perk_name, outcome, user FROM matches
                UNION ALL
                SELECT perk_3_name as perk_name, outcome, user FROM matches
                UNION ALL
                SELECT perk_4_name as perk_name, outcome, user FROM matches
            ) as perks
            {_perksUserFilter}
            GROUP BY perk_name
        """
        _perkRows, _ = self.mRetrieve(_queryPerks)
        
        _perkStats = [{"name": _row[0], "wins": int(_row[1]), "losses": int(_row[2])} for _row in _perkRows]
        
        _topPerks = sorted(_perkStats, key=lambda x: x["wins"], reverse=True)[:5]
        _worstPerks = sorted(_perkStats, key=lambda x: x["losses"], reverse=True)[:5]
        
        _results["top_perks"] = _topPerks
        _results["worst_perks"] = _worstPerks
        
        return _results

    def mGetSuggestion(self, aUser: int, aType: str) -> list[str]:
        # Build SQL selection
        _query = "SELECT DISTINCT p1.name AS perk_name_1, "
        _query += "p2.name AS perk_name_2, p3.name AS perk_name_3, "
        _query += "p4.name AS perk_name_4 "
        # Build view
        _query += "FROM perks p1 "
        _query += "JOIN perk_types pt1 ON p1.id = pt1.perk_id "
        _query += "JOIN perk_types pt2 ON pt1.type_id = pt2.type_id "
        _query += "JOIN perks p2 ON pt2.perk_id = p2.id "
        _query += "JOIN perk_types pt3 ON pt1.type_id = pt3.type_id "
        _query += "JOIN perks p3 ON pt3.perk_id = p3.id "
        _query += "JOIN perk_types pt4 ON pt1.type_id = pt4.type_id "
        _query += "JOIN perks p4 ON pt4.perk_id = p4.id "
        _query += "LEFT JOIN blacklists b1 ON p1.name = b1.perk_name "
        _query += f"AND b1.user_id = {aUser} "
        _query += "LEFT JOIN blacklists b2 ON p2.name = b2.perk_name "
        _query += f"AND b2.user_id = {aUser} "
        _query += "LEFT JOIN blacklists b3 ON p3.name = b3.perk_name "
        _query += f"AND b3.user_id = {aUser} "
        _query += "LEFT JOIN blacklists b4 ON p4.name = b4.perk_name "
        _query += f"AND b4.user_id = {aUser} "
        # Build choice
        _query += "WHERE p1.id < p2.id "
        _query += "AND p2.id < p3.id "
        _query += "AND p3.id < p4.id "
        _query += "AND b1.perk_name IS NULL "
        _query += "AND b2.perk_name IS NULL "
        _query += "AND b3.perk_name IS NULL "
        _query += "AND b4.perk_name IS NULL "
        _query += f"AND pt1.type_id = (SELECT id FROM types WHERE type = \'{aType}\' LIMIT 1) "
        # Build order
        _query += "ORDER BY RAND() "
        _query += "LIMIT 1;"
        # Retrieve results
        _results, _ = self.mRetrieve(_query)
        if len(_results) == 0:
            mLogError(f"Couldn't get SQL results on combos for type: {aType}")
            raise ValueError(f"No suggestions found for perk type '{aType}'. Please ensure the 'perk_types' table is populated.")
        _row = _results[0]
        _cleanResult = [_row[i] for i, _ in enumerate(_row)]
        return _cleanResult
