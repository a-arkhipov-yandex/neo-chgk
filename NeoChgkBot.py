from os import getenv
from dotenv import load_dotenv
import telebot
import telegram
from telebot import types
import re
import requests
from threading import Thread
from log_lib import *
from db_lib import *
from neo_common_lib import *
from question_lib import *
from game_lib import *

ENV_BOTTOKEN = 'BOTTOKEN'
ENV_BOTTOKENTEST = 'BOTTOKENTEST'

ENV_TESTDB = 'TESTDB'
ENV_TESTBOT = 'TESTBOT'

VERSION = '0.9'

CMD_START = '/start'
CMD_HELP = '/help'

CALLBACK_TYPE1_TAG = 'type1answer:'

I_DONT_KNOW_ANSWERR = "!!!Idontknow!!!"

MAX_ANSWER_LENGTH = 256

DEFAULT_ERROR_MESSAGE = '\U00002757 Произошла ошибка. Попробуйте позже.'

#============================
# Common functions
#----------------------------

#=====================
# Bot class
#---------------------
class NeoChgkBot:
    __bot = None

    def registerHandlers(self) -> None:
        NeoChgkBot.__bot.register_message_handler(callback=self.messageHandler, content_types=['text'])
        NeoChgkBot.__bot.register_callback_query_handler(
            callback=self.startGameHandler,
            func=lambda message: re.match(pattern=fr'^{CMD_START}$', string=message.data)
        )

    def initBot(self) -> bool:
        # Check if bot is already initialized
        if (NeoChgkBot.isInitialized()):
            log(str=f'Bot is already initialized', logLevel=LOG_WARNING)
            return False
        # Initialize bot first time
        botToken = getBotToken()
        if (not botToken):
            log(str=f'Cannot read ENV vars: botToken={botToken}', logLevel=LOG_ERROR)
            return False
        NeoChgkBot.__bot = telebot.TeleBot(token=botToken)
        self.registerHandlers()
        isTest = isTestBot()
        log(str=f'Bot initialized successfully (test={isTest})')
        return True

    def isInitialized() -> bool:
        return (NeoChgkBot.__bot != None)

    def getBot(self) -> None | telebot.TeleBot:
        return self.__bot

    # Init bot
    def __init__(self) -> None:
        # Check if bot is initialized
        if (not NeoChgkBot.isInitialized()):
            NeoChgkBot.initBot(self=self)
        self.bot = NeoChgkBot.__bot

    def startBot(self):
        fName = self.startBot.__name__
        if (not NeoChgkBot.isInitialized()):
            log(str=f'{fName}: Bot is not initialized - cannot start', logLevel=LOG_ERROR)
            return False
        log(str=f'Starting bot...')
        while(True):
            try:
                self.bot.infinity_polling()
            except KeyboardInterrupt:
                log(str=f'{fName}: Exiting by user request')
                break
            except requests.exceptions.ReadTimeout as error:
                log(str=f'{fName}: exception: {error}', logLevel=LOG_ERROR)

    # Message handler
    def messageHandler(self, message:types.Message) -> None:
        fName = self.messageHandler.__name__
        username = message.from_user.username
        telegramid = message.from_user.id
        if (not NeoChgkBot.isInitialized()):
            log(str=f'{fName}: Bot is not initialized - cannot start', logLevel=LOG_ERROR)
            return
        # Check if photo recieved
        if (message.text != None):
            # Check if there is a CMD
            if (message.text[0] == '/'):
                return self.cmdHandler(message=message)
            elif (self.checkGameTypeNInProgress(telegramid=telegramid, gameType=1)):
                text = message.text
                return self.answerHandlerType1(telegramid=telegramid, text=text)
        help = self.getHelpMessage(username=username)
        self.sendMessage(telegramid=telegramid, text=f"Я вас не понимаю:(\n{help}")

    # Check is user registered
    def checkUser(self, telegramid) -> bool:
        if (not dbLibCheckTelegramid(telegramid=telegramid)):
            return False
        userId = Connection.getUserIdByTelegramid(telegramid=telegramid)
        if (dbFound(result=userId)):
            return True
        return False

    def cmdHandler(self, message:types.Message) -> None:
        fName = self.cmdHandler.__name__
        telegramid = message.from_user.id
        username = message.from_user.username
        log(str=f'{fName}: Got message cmd "{message.text}"',logLevel=LOG_DEBUG)
        if (not self.checkUser(telegramid=telegramid)):
            # Register new user if not registered yet
            userId = Connection.insertUser(telegramid=telegramid)
            if (not userId):
                log(str=f'{fName}: Cannot register user {username}', logLevel=LOG_ERROR)
                self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
                return
        text = message.text.lower()
        if text == CMD_HELP:
            self.cmdHelpHandler(message=message)
        elif text == CMD_START:
            self.cmdStartHandler(message=message)
        else:
            self.sendMessage(telegramid=telegramid, text="Неизвестная команда.")
            self.sendMessage(telegramid=telegramid, text=self.getHelpMessage(username=message.from_user.username))

    # Send message to user
    # Returns: Message ID or None in case of error
    def sendMessage(self, telegramid, text, parse_mode=None,disable_link_preview=False) -> int | None:
        if (NeoChgkBot.isInitialized()):
            ret = NeoChgkBot.__bot.send_message(chat_id=telegramid, text=text, parse_mode=parse_mode, disable_web_page_preview=disable_link_preview)
            return ret.message_id
        return None

    # /start cmd handler
    def cmdStartHandler(self, message: types.Message) -> None:
        self.startNewGame(telegramid=message.from_user.id)

    # /help cmd handler
    def cmdHelpHandler(self, message:types.Message) -> None:
        help = self.getHelpMessage(username=message.from_user.username)
        self.sendMessage(telegramid=message.from_user.id, text=help)

    # Returns help message
    def getHelpMessage(self, username) -> str:
        if (not NeoChgkBot.isInitialized()):
            log(str=f'Bot is not initialized - cannot start', logLevel=LOG_ERROR)
            return ''
        ret = self.getWelcomeMessage(username=username)
        return ret + f'''
    Команды NeoChgk_Bot:
        {CMD_HELP} - вывести помощь по командам (это сообщение)
        {CMD_START} - регистрация нового пользователя/новая игра
        '''
    # Get welcome message
    def getWelcomeMessage(self, username) -> str:
        usernameMessage = ''
        if (username is not None):
            usernameMessage = f', {username}'
        ret = f'''
        Добро пожаловать{usernameMessage}!
        Это игра "Вопросы из базы Что?Где?Когда?". Версия: {VERSION}
        Все вопросы взяты из базы: https://db.chgk.info/
        Автор: @alex_arkhipov
        '''
        return ret

    def startGameHandler(self, message: types.CallbackQuery) -> None:
        telegramid = message.from_user.id
        self.bot.answer_callback_query(callback_query_id=message.id)
        self.startNewGame(telegramid=telegramid)

    def startNewGame(self, telegramid) -> None:
        fName = self.startNewGame.__name__
        # Check user name format first
        if (not self.checkUser(telegramid=telegramid)):
            log(str=f'{fName}: Unknown user {telegramid} provided',logLevel=LOG_ERROR)
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        # Get game type and complexity
        gameType = Connection.getUserGameType(telegramid=telegramid)
        # Generate new game for the complexity
        params={
            'telegramid':telegramid,
            'type':gameType,
        }
        gameId = generateNewGame(queryParams=params)
        if (gameId is None):
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        self.showQuestion(telegramid=telegramid, type=gameType, gameId=gameId)

    def showQuestion(self,telegramid,type,gameId) -> None:
        fName = self.showQuestion.__name__
        if (not self.checkUser(telegramid=telegramid)):
            log(str=f'{fName}: Unknown user {telegramid} provided',logLevel=LOG_ERROR)
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        if (type == 1):
            self.showQuestionType1(telegramid=telegramid, gameId=gameId)
        else:
            self.sendMessage(telegramid=telegramid, text="Неизваестный тип игры. Пожалуйста, начните новую игру.")

    def showQuestionType1(self,telegramid, gameId) -> None:
        fName = self.showQuestionType1.__name__
        if (not self.checkUser(telegramid=telegramid)):
            log(str=f'{fName}: Unknown user {telegramid} provided',logLevel=LOG_ERROR)
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        # Get gameInfo
        gameInfo = Connection.getGameInfoById(gameId=gameId)
        finished = (gameInfo['result'] is not None)
        if (finished):
            self.sendMessage(telegramid=telegramid, text=f'Извините, но игра уже завершена. Введите "{CMD_START}" чтобы начать новую.')
            return
        question = decodeQuestion(pickle_question=gameInfo['question'])
        textQuestion = question.getHTMLQuestion()
        if (question.pic):
            log(str=f'{fName}: Question with picture: {url}',logLevel=LOG_DEBUG)
            url = question.pic
            self.bot.send_photo(chat_id=telegramid, photo=url, caption=textQuestion, parse_mode='html',disable_web_page_preview=True)
        else:
            log(str=f'{fName}: Question without picture',logLevel=LOG_DEBUG)
            self.sendMessage(telegramid=telegramid, text=textQuestion, parse_mode='html',disable_link_preview=True)
        self.bot.send_message(chat_id=telegramid, text='Введите ваш вариант ответа:')

    # Send buttons after answer
    def sendAfterAnswer(self, telegramid) -> None:
        fName = self.sendAfterAnswer.__name__
        if (not self.checkUser(telegramid=telegramid)):
            log(str=f'{fName}: Unknown user {telegramid} provided',logLevel=LOG_ERROR)
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        key1 = types.InlineKeyboardButton(text='\U0001F4AA Сыграть еще раз', callback_data=CMD_START)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(key1)
        question = 'Выберите дальнейшее действие:'
        self.bot.send_message(chat_id=telegramid, text=question, reply_markup=keyboard)
    
    def answerHandlerType1(self, telegramid, text) -> None:
        fName = self.answerHandlerType1.__name__
        if (not self.checkUser(telegramid=telegramid)):
            log(str=f'{fName}: Unknown user {telegramid} provided',logLevel=LOG_ERROR)
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        # Get current game
        gameId = Connection.getCurrentGame(telegramid=telegramid)
        if (not gameId):
            self.sendMessage(telegramid=telegramid, text='Нет запущенных игр. Введите "/start" чтобы начать новую.')
            return
        # Get question info
        gameInfo = Connection.getGameInfoById(gameId=gameId)
        question = decodeQuestion(pickle_question=gameInfo['question'])

        # Limit answer length
        if (len(text) > MAX_ANSWER_LENGTH):
            text = text[:MAX_ANSWER_LENGTH]
            log(str=f'Слишком длинный ответ - обрезаю ({text})', logLevel=LOG_WARNING)

        # Finish game and return result
        finishGame(telegramid=telegramid, gameInfo=gameInfo, answer=text)
        # Get game info
        gameInfo = Connection.getGameInfoById(gameId=gameId)
        # Check result
        result = gameInfo['result']
        self.showGameResult(telegramid=telegramid, result=result, question=question)
    
    # Show game result
    def showGameResult(self, telegramid, result, question: ChgkQuestion, dont_know=False) -> None:
        correctAnswer = question.getHTMLAnswer()
        # Check result
        if (result):
            # Answer is correct
            text = f"\U0001F3C6 Поздравляю! Вы ответили верно.\n"
            text += f"{correctAnswer}"
            self.sendMessage(telegramid=telegramid, text=text, parse_mode='html',disable_link_preview=True)
        else:
            reply_end = f'{correctAnswer}'
            reply_start = f"\U0000274C А вот и не верно.\n"
            if (dont_know):
                reply_start = f'\U0001F9E0 Теперь будете знать.'                
            self.sendMessage(telegramid=telegramid, text=f'{reply_start}{reply_end}', parse_mode='html',disable_link_preview=True)
        self.sendAfterAnswer(telegramid=telegramid)

    # Check that game N is in progress
    # Returns: True/False
    def checkGameTypeNInProgress(self, telegramid, gameType) -> bool:
        fName = self.checkGameTypeNInProgress.__name__
        userName = telegramid
        if (not self.checkUser(telegramid=telegramid)):
            log(str=f'{fName}: Unknown user {telegramid} provided',logLevel=LOG_ERROR)
            self.sendMessage(telegramid=telegramid, text=DEFAULT_ERROR_MESSAGE)
            return
        ret = Connection.getCurrentGame(telegramid=userName)
        if (dbFound(result=ret)):
            gameInfo = Connection.getGameInfoById(gameId=ret)
            if (dbFound(result=gameInfo)): # Game info is valid
                if (gameInfo['game_type'] == gameType):
                    return True
            else:
                log(str=f'{fName}: Cannot get gameInfo from DB: {ret}', logLevel=LOG_ERROR)
        return False