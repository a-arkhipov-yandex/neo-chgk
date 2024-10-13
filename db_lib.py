from time import sleep
from threading import Thread
import psycopg2
from log_lib import *
from neo_common_lib import *

ENV_DBHOST = 'DBHOST'
ENV_DBPORT = 'DBPORT'
ENV_DBNAME = 'DBNAME'
ENV_DBUSER = 'DBUSER'
ENV_DBTOKEN ='DBTOKEN'
ENV_DBTESTHOST = 'DBTESTHOST'
ENV_DBTESTPORT = 'DBTESTPORT'
ENV_DBTESTNAME = 'DBTESTNAME'
ENV_DBTESTUSER = 'DBTESTUSER'
ENV_DBTESTTOKEN ='DBTESTTOKEN'

ENV_TESTDB = 'TESTDB'

NOT_FOUND = "!!!NOT_FOUND!!!"

DEFAULT_GAMETYPE = 1

#=======================
# Common functions section
#-----------------------
# Check that item not found
# Returns:
#   True - item was not found
#   False - otherwise (found or error)
def dbNotFound(result) -> bool:
    if (result != None):
        if (result == NOT_FOUND): # empty array
            return True
    return False

# Check that item is found
# Returns:
#   True - item has been found
#   False - otherwise (not found or error)
def dbFound(result) -> bool:
    if (result != None):
        if (result != NOT_FOUND): # empty array
            return True
    return False

# Check user name (can be string with '[a-zA-Z][0-9a-zA-Z]')
def dbLibCheckTelegramid(telegramid) -> bool:
    if (telegramid is None):
        return False
    ret = False
    try:
        tInt = int(telegramid) # Check that it is valid int value
        if (tInt > 0):
            ret = True
    except:
        pass
    return ret

# Check user id (can be string or int with positive integer value)
def dbLibCheckUserId(userId) -> bool:
    ret = False
    iId = 0
    try:
        iId = int(userId)
    except:
        pass
    if (iId > 0):
        ret = True
    return ret

# Check if game is finished
# Input:
#   gameInfo - data
# Returns: True/False
def dbLibCheckIfGameFinished(gameInfo:dict) -> bool:
    result = gameInfo.get('result')
    if (result != None):
        return True
    return False
    
# Make useful map for game
def dbGetGameInfo(queryResult) -> dict:
    game = {}
    if (len(queryResult) != 9):
        return game
    game['id'] = int(queryResult[0])
    game['userid'] = int(queryResult[1])
    game['game_type'] = int(queryResult[2])
    game['question'] = queryResult[3]
    game['correct_answer']  = queryResult[4]
    game['user_answer']  = queryResult[5]
    game['result'] = queryResult[6]
    game['created'] = queryResult[7]
    game['finished'] = queryResult[8]
    return game

#==================
# Class definition
#------------------
class Connection:
    __connection = None
    __isInitialized = False
    __defaultGameType = DEFAULT_GAMETYPE
    __thread = None
    loopFlag = True

    # Init connection - returns True/False
    def initConnection(test=False) -> bool:
        ret = False
        if (not Connection.__isInitialized):
            Connection.__newConnection(test=test)
            if (Connection.isActive()):
                # Cache section
                Connection.__gameTypes = Connection.getGameTypesFromDb()
                Connection.__test = test
                log(str=f"DB Connection created (test={test})", logLevel=LOG_DEBUG)
                ret = True
            else:
                log(str=f'Cannot initialize connection to DB',logLevel=LOG_ERROR)
        else:
                log(str=f'Trying to initialize connection that already initialized',logLevel=LOG_WARNING)
        return ret
    
    def getConnection():
        return Connection.__connection
    
    def closeConnection() -> None:
        if (Connection.isActive()):
            Connection.pingStop()
            Connection.__isInitialized = False
            Connection.__connection.close()
            log(str=f"DB Connection closed")
        else:
            log(str=f"DB Connection already closed",logLevel=LOG_WARNING)

    def __newConnection(test=False) -> bool:
        # Check if connection is open
        if (Connection.isActive()):
            log(str=f"Closing connection to DB",logLevel=LOG_WARNING)
            Connection.closeConnection()
        ret = False
        if (test):
            data = getDBbTestConnectionData()
        else: # Production
            data = getDBbConnectionData()
        if (data is None):
            log(str=f'Cannot get env data. Exiting.',logLevel=LOG_ERROR)
            return False
        try:
            Connection.__connection = psycopg2.connect(dsn=f"""
                host={data['dbhost']}
                port={data['dbport']}
                sslmode=verify-full
                dbname={data['dbname']}
                user={data['dbuser']}
                password={data['dbtoken']}
                target_session_attrs=read-write
            """)
            Connection.__connection.autocommit = True
            Connection.__isInitialized = True
            Connection.startPingTask()
            ret = True
            log(str=f'DB Connetion established')
        except (Exception, psycopg2.DatabaseError) as error:
            log(str=f"Cannot connect to database: {error}",logLevel=LOG_ERROR)
        return ret

    def isInitialized() -> bool:
        return Connection.__isInitialized

    def isActive() -> bool:
        return Connection.__isInitialized and Connection.getConnection().closed == 0

    def reconnect() -> bool:
        # check if connection was initialized before
        if (not Connection.isInitialized()):
            log(str='Connection was not initialized. Cannot reconnect.', logLevel=LOG_ERROR)
            return False
        if (not Connection.isActive()):
            Connection.pingStop()
            return Connection.__newConnection(test=Connection.__test)

    # Execute query with params
    # If 'all' == True - execute fetchAll()/ otherwise fetchOne()
    # Returns:
    #   None - issue with execution
    #   NOT_FOUND - if nothing found
    #   [result] - array with one/many found item(s)
    def executeQuery(query, params={}, all=False):
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f'Cannot execute query "{query}" with "{params}" (all={all}): connection is not ready', logLevel=LOG_ERROR)
            return None
        ret = NOT_FOUND
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            try:
                cur.execute(query=query,vars=params)
                if (all):
                    res = cur.fetchall()
                    if (len(res) == 0):
                        ret = NOT_FOUND
                    else:
                        ret = []
                        for i in res:
                            tmp = []
                            for j in i:
                                tmp.append(j)
                            ret.append(tmp)
                else:
                    res = cur.fetchone()
                    if (res):
                        if (len(res) == 0):
                            ret = NOT_FOUND
                        else:
                            ret = []
                            for i in res:
                                ret.append(i)
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'Failed execute query "{query}" with params "{params}" (all={all}): {error}',logLevel=LOG_ERROR)
                return None
        return ret
    
    #==========================
    # Check functions
    #--------------------------
    # Check game type (can be string or int with value 1 or 2)
    def dbLibCheckGameType(game_type) -> bool:
        ret = False
        iType = 0
        try:
            iType = int(game_type)
        except:
            return ret
        gameTypes = Connection.getGameTypes()
        if (iType >= 1 and iType <= len(gameTypes)):
            ret = True
        return ret

    #==========================
    # Settings section
    #--------------------------
    # Get setting value. Returns key or None if not found or if connection is not initialized
    def getSettingValue(key):
        query = 'select value from settings where key=%(key)s'
        ret = Connection.executeQuery(query=query,params={'key': key})
        if (dbFound(result=ret)):
            ret = ret[0]
        return ret

    # Get game types from DB
    # Returns:
    #   [[game_type_id, name]]
    #   NOT_FOUND - no game_types in DB
    #   None - issue with connection
    def getGameTypesFromDb():
        query = 'select id,name from game_types order by id asc'
        ret = Connection.executeQuery(query=query,params={},all=True)
        return ret

    # Get game types from cache
    # Returns:
    #   [[game_type_id, name, question]]
    #   None - connection not initialized
    def getGameTypes():
        if (Connection.isInitialized()):
            return Connection.__gameTypes
        return None

    # Get default game type from cache
    # Returns:
    #   game_type_id
    #   None - connection not initialized
    def getDefaultGameType():
        if (Connection.isInitialized()):
            return Connection.__defaultGameType
        return None

    #==========================
    # User section
    #--------------------------

    # Get all settings for user
    # Returns:
    #   NOT_FOUND - no such user
    #   None - issue with DB
    #   [game_type,game_complexity]
    def getUserSetting(telegramid):
        # Get user id
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbFound(result=userId)):
            query = 'select game_type from users where id=%(id)s'
            ret = Connection.executeQuery(query=query,params={'id':userId})
        else:
            ret = userId
        return ret

    # Get user by name
    # Return:
    #   None - something wrong with connection/query
    #   id - user id
    #   NOT_FOUND - no such user
    def getUserIdByTelegramid(telegramid):
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            return NOT_FOUND
        query = f"SELECT id FROM users WHERE telegramid = %(tid)s"
        ret = Connection.executeQuery(query=query,params={'tid':telegramid})
        if (dbFound(result=ret)):
            ret = ret[0]
        return ret

    # Delete user - returns True/False
    def deleteUser(userId) -> bool:
        fName = Connection.deleteUser.__name__
        ret = False
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: Cannot delete user - connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            query = "DELETE from users where id = %(user)s"
            try:
                cur.execute(query=query, vars={'user':userId})
                log(str=f'{fName}: Deleted user: {userId}')
                ret = True
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'{fName}: Failed delete user {userId}: {error}',logLevel=LOG_ERROR)
        return ret
    
    # Insert new user in DB. 
    #   Returns:
    #      user id - if success
    #      None - if any error
    def insertUser(telegramid, gameType=None):
        fName = Connection.insertUser.__name__
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            log(str=f"{fName}: Cannot insert user -  invalid telegramid format: {telegramid}",logLevel=LOG_ERROR)
            return None
        if ((gameType is None) or (not Connection.dbLibCheckGameType(game_type=gameType))):
            gameType = Connection.getDefaultGameType()
        ret = None
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: Cannot insert user - connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        # Check for duplicates
        retUser = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (retUser is None): # error with DB
            log(str=f'{fName}: Cannot get user from DB: {telegramid}',logLevel=LOG_ERROR)
            return None
        if (dbNotFound(result=retUser)):
            with conn.cursor() as cur:
                query = "INSERT INTO users ( telegramid,game_type ) VALUES ( %(u)s,%(t)s ) returning id"
                try:
                    cur.execute(query=query, vars={'u':telegramid,'t':gameType})
                    row = cur.fetchone()
                    if (row):
                        ret = row[0]
                        log(str=f'{fName}: Inserted user: {telegramid} - {gameType}')
                    else:
                        log(str=f'{fName}: Cannot get id of new user: {query}',logLevel=LOG_ERROR)
                except (Exception, psycopg2.DatabaseError) as error:
                    log(str=f'{fName}: Failed insert user {telegramid}: {error}',logLevel=LOG_ERROR)
        else:
            log(str=f'{fName}: Trying to insert duplicate user: {telegramid}',logLevel=LOG_WARNING)
            ret = None
        return ret

    # Get current game data for user userName
    # Returns:
    # id - current game id
    # None - no current game
    def getCurrentGameData(telegramid):
        fName = Connection.getCurrentGameData.__name__
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            log(str=f'{fName}: Incorrect user {telegramid} provided',logLevel=LOG_ERROR)
            return None
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbNotFound(result=userId)):
            log(str=f'{fName}: Cannot find user {telegramid}',logLevel=LOG_ERROR)
            return None
        ret = None
        query = 'select game_data from users where id=%(uId)s'
        currentGameData = Connection.executeQuery(query=query, params={'uId':userId})
        if (dbFound(result=currentGameData)):
            currentGameData = currentGameData[0]
            if (currentGameData):
                ret = currentGameData
        return ret
    
    # Get user game type
    # Returns:
    #   game_type - game type
    #   None - if error
    def getUserGameType(telegramid):
        fName = Connection.getUserGameType.__name__
        ret = None
        if (not Connection.isInitialized()):
            log(str=f"{fName}: connection is not initialized",logLevel=LOG_ERROR)
            return ret
        ret2 = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret2):
            log(str=f'{fName}: Incorrect user {telegramid} provided',logLevel=LOG_ERROR)
            return ret
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbNotFound(result=userId)):
            log(str=f'{fName}: Cannot find user {telegramid}',logLevel=LOG_ERROR)
            return ret
        query = f'select game_type from users where id=%(uId)s'
        ret2 = Connection.executeQuery(query=query,params={'uId':userId})
        if (dbFound(result=ret2)):
            ret = ret2[0]
        return ret

    # Update game type for the userId
    # Returns: True - update successful / False - otherwise
    def updateUserGameType(telegramid, gameType) -> bool:
        fName = Connection.updateUserGameType.__name__
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            log(str=f'{fName}: Incorrect user {telegramid} provided',logLevel=LOG_ERROR)
            return False
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbNotFound(result=userId)):
            log(str=f'{fName}: Cannot find user {telegramid}',logLevel=LOG_ERROR)
            return False
        if (not Connection.dbLibCheckGameType(game_type=gameType)):
            log(str=f'{fName}: Wrong game type format: {gameType}',logLevel=LOG_ERROR)
            return False

        ret = False
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: Connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            query = 'update users set game_type=%(gt)s where id = %(uId)s'
            try:
                cur.execute(query=query,vars={'gt':gameType,'uId':userId})
                log(str=f'{fName}: Updated game type: (user={telegramid} | gameType = {gameType})')
                ret = True
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'{fName}: Failed update game type (gameType = {gameType}, user={telegramid}): {error}',logLevel=LOG_ERROR)
        return ret

    # Get current game for user userName
    # Returns:
    # id - current game id
    # None - no current game
    def getCurrentGame(telegramid):
        fName = Connection.getCurrentGame.__name__
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            log(str=f'{fName}: Incorrect user {telegramid} provided',logLevel=LOG_ERROR)
            return None
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbNotFound(result=userId)):
            log(str=f'{fName}: Cannot find user {telegramid}',logLevel=LOG_ERROR)
            return None
        ret = None
        query = 'select current_game from users where id=%(uId)s'
        currentGame = Connection.executeQuery(query=query, params={'uId':userId})
        if (dbFound(result=currentGame)):
            currentGame = currentGame[0]
            if (currentGame):
                # Check that game is not finished
                ret2 = Connection.checkGameIsFinished(gameId=currentGame)
                if (not ret2): # UnFinished game
                    ret = currentGame
                else:
                    log(str=f'{fName}: Current game {currentGame} is finished for user {userId} - clear current game')
                    Connection.clearCurrentGame(telegramid=telegramid)
        return ret
    
    def setCurrentGameData(telegramid, gameData) -> bool:
        return Connection.updateCurrentGameData(telegramid=telegramid, gameData=gameData)

    def clearCurrentGameData(telegramid) -> bool:
        return Connection.updateCurrentGameData(telegramid=telegramid, gameData=None)

    # Update game_data for the userId
    # Returns: True - update successful / False - otherwise
    def updateCurrentGameData(telegramid, gameData) -> bool:
        fName = Connection.updateCurrentGameData.__name__
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            log(str=f'{fName}: Incorrect user {telegramid} provided',logLevel=LOG_ERROR)
            return False
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbNotFound(result=userId)):
            log(str=f'{fName}: Cannot find user {telegramid}',logLevel=LOG_ERROR)
            return False
        ret = False
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            query = 'update users set game_data=%(gd)s where id = %(uId)s'
            try:
                cur.execute(query=query,vars={'gd':gameData,'uId':userId})
                log(str=f'{fName}: Updated current game data: (user={telegramid} | gameData = {gameData})')
                ret = True
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'{fName}: Failed update current game data (gameData = {gameData}, user={telegramid}): {error}',logLevel=LOG_ERROR)
        return ret

    def setCurrentGame(telegramid, gameId) -> bool:
        return Connection.updateCurrentGame(telegramid=telegramid, gameId=gameId)

    def clearCurrentGame(telegramid) -> bool:
        return Connection.updateCurrentGame(telegramid=telegramid, gameId=None)

    # Update current_game for the userId
    # Returns: True - update successful / False - otherwise
    def updateCurrentGame(telegramid, gameId) -> bool:
        fName = Connection.updateCurrentGame.__name__
        ret = dbLibCheckTelegramid(telegramid=telegramid)
        if (not ret):
            log(str=f'{fName}: Incorrect user {telegramid} provided',logLevel=LOG_ERROR)
            return False
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbNotFound(result=userId)):
            log(str=f'{fName}: Cannot find user {telegramid}',logLevel=LOG_ERROR)
            return False
        if (gameId):
            gameInfo = Connection.getGameInfoById(gameId=gameId)
            if (gameInfo is None or dbNotFound(result=gameInfo)):
                log(str=f'{fName}: cannot find game {gameId} (user={telegramid})',logLevel=LOG_ERROR)
                return False
            # Check userId is correct
            if (gameInfo['userid'] != userId):
                log(str=f'{fName}: game {gameId} doesnt belong to user {telegramid} ({userId})',logLevel=LOG_ERROR)
                return False
            # Check that game is finished
            ret = dbLibCheckIfGameFinished(gameInfo=gameInfo)
            if (ret):
                log(str=f'{fName}: cannot set finished game as current (gameId = {gameId}, user={telegramid})',logLevel=LOG_ERROR)
                return False
        ret = False
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            query = 'update users set current_game=%(gId)s where id = %(uId)s'
            try:
                cur.execute(query=query,vars={'gId':gameId,'uId':userId})
                log(str=f'{fName}: Updated current game: (user={telegramid} | gameId = {gameId})')
                ret = True
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'{fName}: Failed update current game (gameId = {gameId}, user={telegramid}): {error}',logLevel=LOG_ERROR)
        return ret

    #=======================
    # Game serction
    #-----------------------
    # Delete game - returns true/false
    def deleteGame(gameId) -> bool:
        fName = Connection.deleteGame.__name__
        ret = False
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: Cannot delete game - connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            query = "DELETE from games where id = %(id)s"
            try:
                cur.execute(query=query, vars={'id':gameId})
                log(str=f'{fName}: Deleted game: {gameId}')
                ret = True
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'{fName}: Failed delete game {gameId}: {error}',logLevel=LOG_ERROR)
        return ret
    
    # Insert new game in DB
    # Returns:
    #   id - id of new game
    #   None - otherwise
    def insertGame(userId, game_type, question, correct_answer):
        fName = Connection.insertGame.__name__
        # Checks first
        if (not dbLibCheckUserId(userId=userId)):
            return None
        if (not Connection.dbLibCheckGameType(game_type=game_type)):
            return None
        ret = None
        if (not Connection.isActive() and not Connection.reconnect()):
            log(str=f"{fName}: Cannot insert game - connection is not initialized",logLevel=LOG_ERROR)
            return ret
        conn = Connection.getConnection()
        with conn.cursor() as cur:
            params = {'u':userId,'t':game_type,'q':question,'ca':correct_answer}
            query = 'INSERT INTO games (userid,game_type,question,correct_answer,created) VALUES ( %(u)s, %(t)s, %(q)s, %(ca)s, NOW()) returning id'
            try:
                cur.execute(query=query, vars=params)
                row = cur.fetchone()
                if (row):
                    ret = row[0]
                    log(str=f'Inserted game: {ret}')
                else:
                    log(str=f'{fName}: Cannot get id of new game: {query}',logLevel=LOG_ERROR)
            except (Exception, psycopg2.DatabaseError) as error:
                log(str=f'{fName}: Failed insert game for user {userId}: {error}',logLevel=LOG_ERROR)
        return ret

    # Get game by id
    # Returns:
    #   None - issue with DB
    #   NOT_FOUND - no such game
    #   {gameInfo} - game info
    def getGameInfoById(gameId):
        query = 'select id,userid,game_type,question,correct_answer,user_answer,result,created,finished from games where id = %(id)s'
        ret = Connection.executeQuery(query=query,params={'id':gameId})
        if (dbFound(result=ret)):
            gameInfo = dbGetGameInfo(queryResult=ret)
            ret = gameInfo
        return ret

    # Finish game
    # Input:
    #   gameId - game id
    #   answer - user_answer
    # Result:
    #   False - issue with DB
    #   True - successful finish
    def finishGame(gameId, answer) -> bool:
        fName = Connection.finishGame.__name__
        gameInfo = Connection.getGameInfoById(gameId=gameId)
        if (gameInfo is None):
            log(str=f'{fName}: cannot get game {gameId}: DB issue',logLevel=LOG_ERROR)
            return False
        ret = False
        if (dbFound(result=gameInfo)):
            # Check that game is not finished yet
            isFinished = dbLibCheckIfGameFinished(gameInfo=gameInfo)
            if (isFinished):
                log(str=f'{fName}: Game {gameId} is already finished',logLevel=LOG_WARNING)
                return False
            # Check result by answer
            correct_answer = gameInfo['correct_answer']
            dbResult = 'false'
            if (answer == correct_answer):
                dbResult = 'true'
            if (not Connection.isActive() and not Connection.reconnect()):
                log(str=f"{fName}: Cannot finish game - connection is not initialized",logLevel=LOG_ERROR)
                return False
            conn = Connection.getConnection()
            with conn.cursor() as cur:
                query = 'update games set finished = NOW(), result=%(r)s, user_answer=%(a)s where id = %(id)s'
                try:
                    cur.execute(query=query,vars={'r':dbResult,'id':gameId, 'a':answer})
                    log(str=f'{fName}: Finished game: {gameId} - {dbResult}')
                    ret = True
                except (Exception, psycopg2.DatabaseError) as error:
                    log(str=f'{fName}: Failed finish game {gameId}: {error}',logLevel=LOG_ERROR)
        else:
            log(str=f"{fName}: Cannot find game {gameId}: game not found",logLevel=LOG_ERROR)
        return ret
    
    # Check is game is finished. Returns True/False
    def checkGameIsFinished(gameId) -> bool:
        gameInfo = Connection.getGameInfoById(gameId=gameId)
        if (dbFound(result=gameInfo)):
            return (dbLibCheckIfGameFinished(gameInfo=gameInfo))
        return False

    #######################
    # Reconnect section
    #----------------------

    def startPingTask() -> None:
        Connection.loopFlag = True
        Connection.__thread = Thread(target=Connection.dbPingTask)
        Connection.__thread.start()

    def pingStop() -> None:
        Connection.loopFlag = False
        if (not Connection.__thread):
            log(str='Ping thread is not active', logLevel=LOG_WARNING)
        Connection.__thread.join()
        Connection.__thread = None

    def dbPingTask() -> None:
        SLEEP_INTERVAL = 5
        fName = Connection.dbPingTask.__name__
        log(str=f'{fName}: thread started')
        # infinite loop
        while(Connection.loopFlag):
            # Make simple select to check if DB is active
            query = 'select id from users limit 1'
            res = Connection.executeQuery(query=query,params={},all=False)
            if (res is None):
                log(str=f'{fName}: Database is not active, reconnecting')
                if (not Connection.reconnect()):
                    log(str=f'{fName}: Cannot reconnect to database', logLevel=LOG_WARNING)
            sleep(SLEEP_INTERVAL)

        log(str=f'{fName}: thread stopped')
