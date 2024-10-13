from __future__ import annotations

import pytest

from datetime import datetime as dt, timedelta
from db_lib import *
from question_lib import *

class TestDB:
    testUserTelegramId1 = '123456789'
    testUserTelegramId2 = "987654321"
    testUserId1 = None
    testUserId2 = None
    testPersonId1 = None
    testPersonId2 = None
    testPersonId3 = None
    testImageId1 = None
    testImageId2 = None
    testImageId3 = None
    testImageId4 = None
    testImageId5 = None
    testImageId21 = None

    def testDBConnectoin(self) -> None: # Test both test and production connection
        initLog(printToo=True)
        Connection.initConnection(test=False) # prod connection
        isInit1 = Connection.isInitialized()
        Connection.closeConnection()
        Connection.initConnection(test=True) # test connections
        isInit2 = Connection.isInitialized()
        # Create test user
        TestDB.testUserId1 = Connection.insertUser(telegramid=TestDB.testUserTelegramId1) # fake telegramid
        assert(TestDB.testUserId1 is not None)
        game_type = Connection.getUserSetting(telegramid=TestDB.testUserTelegramId1)
        assert(game_type[0] == DEFAULT_GAMETYPE)
        game_type = Connection.getUserSetting(telegramid=TestDB.testUserTelegramId1)
        assert(len(Connection.getGameTypes()) > 0)
        userId = Connection.getUserIdByTelegramid(telegramid=TestDB.testUserTelegramId1)
        assert(userId == TestDB.testUserId1)
        TestDB.testUserId2 = Connection.insertUser(telegramid=TestDB.testUserTelegramId2) # fake telegramid
        id_tmp = Connection.insertUser(telegramid=TestDB.testUserTelegramId2) # fake telegramid
        assert(id_tmp is None)
        assert(isInit1 and isInit2)
        assert(TestDB.testUserId1 and TestDB.testUserId2)

    @pytest.mark.parametrize(
        "query, params, expected_result",
        [
            # Correct
            ('select id from users where id = 1000000', {}, NOT_FOUND), # Correct query wihtout params returning nothing
            ('select id from users where id = %(c)s', {'c':1000000}, NOT_FOUND), # Correct query with 1 param returning nothing
            ('select id from users where id=%(c)s and telegramid=%(n)s', {'c':1000000, 'n':'12'}, NOT_FOUND), # Correct query with >1 params returning nothing
            # Incorrect
            ('select id from users where people = 10', {}, None), # InCorrect query syntax
            ('select id from users where id = %(c)s', {}, None), # InCorrect query need params but not provided
            ('select id from users where id=%(c)s and name=%(n)s', {'c':1000000}, None), # InCorrect number of params in query
        ],
    )
    def testExecuteQueryFetchOne(self, query, params, expected_result):
        assert(Connection.executeQuery(query=query, params=params) == expected_result)

    @pytest.mark.parametrize(
        "query, params, expected_result",
        [
            # Correct
            ('select id from users where id = 1000000', {}, NOT_FOUND), # Correct query wihtout params returning nothing
            ('select id from users where id = %(c)s', {'c':1000000}, NOT_FOUND), # Correct query with 1 param returning nothing
            ('select id from users where id=%(c)s and telegramid=%(n)s', {'c':1000000, 'n':'123'}, NOT_FOUND), # Correct query with >1 params returning nothing
            # Incorrect
            ('select id from users where people = 10', {}, None), # InCorrect query syntax
            ('select id from users where id = %(c)s', {}, None), # InCorrect query need params but not provided
            ('select id from users where id=%(c)s and name=%(n)s', {'c':1000000}, None), # InCorrect number of params in query
        ],
    )
    def testExecuteQueryFetchAll(self, query, params, expected_result):
        assert(Connection.executeQuery(query=query, params=params, all=True) == expected_result)

    # Test user name format
    @pytest.mark.parametrize(
        "p, expected_result",
        [
            ('123dfdf', False),
            ('dfввв12', False),
            ('s232', False),
            ('232', True),
            ('s23#2', False),
            ('s/232', False),
            ('s#232', False),
            ('s$232', False),
            ('s%232', False),
            ('s2.32', False),
            ('-123', False),
            ('alex_arkhipov', False),
        ],
    )
    def testCheckUserTelegramFormat(self, p, expected_result):
        ret = dbLibCheckTelegramid(telegramid=p)
        assert(ret == expected_result)

    # Test dbLibCheckUserId
    @pytest.mark.parametrize(
        "u, expected_result",
        [
            (128, True),
            ('12', True),
            ('s232', False),
            ('s23#2', False),
            ('s/232', False),
            ('-123', False),
            ('0', False),
        ],
    )
    def testdbLibCheckUserId(self, u, expected_result):
        ret = dbLibCheckUserId(userId=u)
        assert(ret == expected_result)

    # Test dbLibCheckGameType()
    def testdbLibCheckGameType(self) -> None:
        gameTypes = Connection.getGameTypes()
        ret = Connection.dbLibCheckGameType(game_type=0)
        assert(ret == False)
        ret = Connection.dbLibCheckGameType(game_type=len(gameTypes))
        assert(ret == True)
        ret = Connection.dbLibCheckGameType(game_type=len(gameTypes)+1)
        assert(ret == False)
        ret = Connection.dbLibCheckGameType(game_type="dfdf")
        assert(ret == False)

    def testGame(self) -> None:
        # Create game type 1
        correct_answer = "correct_answer"
        questionText = 'queston'
        question = encodeQuestion(Q=ChgkQuestion(
            question=questionText,
            answer='correct_answer',
        ))
        gameId1 = Connection.insertGame(userId=TestDB.testUserId1,game_type=1,correct_answer=correct_answer,question=question)
        assert(gameId1 is not None)
        gameInfo = Connection.getGameInfoById(gameId=gameId1)
        assert(gameInfo['id'] == gameId1)
        assert(gameInfo['userid'] == TestDB.testUserId1)
        assert(gameInfo['game_type'] == 1)
        assert(gameInfo['created'] != None)
        assert(gameInfo['user_answer'] is None)
        decodedQuestion = decodeQuestion(pickle_question=gameInfo['question'])
        assert(decodedQuestion.question == questionText)
        assert(decodedQuestion.answer == correct_answer)
        # Create game type 2
        gameId2 = Connection.insertGame(userId=TestDB.testUserId2,game_type=1,correct_answer=correct_answer,question=question)
        assert(gameId2 is not None)
        assert(Connection.checkGameIsFinished(gameId=gameId2) == False)
        # Complete game type 1 with correct answer
        Connection.finishGame(gameId=gameId1,answer=correct_answer)
        # Check result game 1
        gameInfo = Connection.getGameInfoById(gameId=gameId1)
        assert(gameInfo['result'] == True)
        assert(gameInfo['finished'] != None)
        # Complete game type 2 with incorrect answer
        Connection.finishGame(gameId=gameId2,answer=1)
        # Check result game 2
        gameInfo = Connection.getGameInfoById(gameId=gameId2)
        assert(gameInfo['result'] == False)
        assert(Connection.checkGameIsFinished(gameId=gameId1) == True)
        # Delete game 1
        assert(Connection.deleteGame(gameId=gameId1))
        # Delete game 2
        assert(Connection.deleteGame(gameId=gameId2))

    def testClenup(seft) -> None:
        # Remove test user
        resDelete1 = False
        resDelete2 = False
        resDelete1 = Connection.deleteUser(userId=TestDB.testUserId1)
        resDelete2 = Connection.deleteUser(userId=TestDB.testUserId2)
        # Close connection
        Connection.closeConnection()
        assert(resDelete1)
        assert(resDelete2)

