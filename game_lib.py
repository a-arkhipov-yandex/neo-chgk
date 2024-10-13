from question_lib import *
from db_lib import *


# Generate new game
# Returns:
#   None - if error
#   id - new game id
def generateNewGame(queryParams):
    fName = generateNewGame.__name__
    ret = None
    game_type = queryParams.get('type')
    if (not Connection.dbLibCheckGameType(game_type=game_type)):
        log(str=f'{fName}: game type is incorect ({game_type})',logLevel=LOG_ERROR)
        return None
    game_type = int(game_type)
    if (game_type == 1):
        ret = generateNewGame1(queryParams=queryParams)
    else:
        log(str=f'{fName}: Unknown game type {game_type}',logLevel=LOG_ERROR)
    return ret

# Generate new game with type 1: guess image of the person
# Returns:
#   None - is any error
#   gameId - id of new game
def generateNewGame1(queryParams):
    fName = generateNewGame1.__name__

    telegramid = queryParams['telegramid']
    userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
    if (userId is None or dbNotFound(result=userId)):
        log(str=f'{fName}: Cannot get user id by telegramid {telegramid}',logLevel=LOG_ERROR)
        return None
    gameType = queryParams['type']
    # Get new question
    question = get_chgk_question()
    if (not question):
        return None
    # Create new game with question (pickled)
    encoded_question = encodeQuestion(Q=question)
    ret = Connection.insertGame(userId=userId, game_type=gameType, question=encoded_question, correct_answer=question.answer)
    if (ret is None):
        log(str=f'{fName}: Cannot insert game u={telegramid},gt={gameType},q={question}',logLevel=LOG_ERROR)
        return None
    else:
        # Set current_game
        Connection.setCurrentGame(telegramid=telegramid, gameId=ret)
    return ret

# Finish game
# Returns: True/False
def finishGame(telegramid, gameInfo, answer) -> bool:
    # Check answer first
    if (checkCorrectAnswer(correct_answer=gameInfo['correct_answer'], answer=answer)):
        answer = gameInfo['correct_answer']
    ret =  Connection.finishGame(gameId=gameInfo['id'], answer=answer)
    if (not ret):
        return False
    # Clear current game
    Connection.clearCurrentGame(telegramid=telegramid)
    Connection.clearCurrentGameData(telegramid=telegramid)
    return True