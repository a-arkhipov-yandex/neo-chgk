import requests
from requests.exceptions import RequestException, JSONDecodeError
import xmltodict
import re
import pickle
from log_lib import *
from db_lib import *
from neo_common_lib import *

CHGK_URL = "https://db.chgk.info/xml/random/answers/types1/912864593/limit1"
PICTURE_URL = "https://db.chgk.info/images/db/"

MAX_QUESTION_LENGTH = 2048
MIN_SIMILARITY = 3

def isStrSimilar(str1,str2) -> bool:
    dist = getStrDistance(str1=str1,str2=str2)
    return dist <= MIN_SIMILARITY

##############################
class ChgkQuestion:
    def __init__(self, question: str, answer:str,
                 questionPicture=None, commentPicture=None, comment=None, authors=None,
                 tournament=None, date=None, sources=None, pass_criteria=None) -> None:
        question = question
        self.question = question
        self.answer = answer
        # Remove trialing dots
        if (answer[-1] == '.'):
            self.answer = answer[:-1]
        self.__questionPictureUrl = questionPicture
        self.__commentPictureUrl = commentPicture
        self.comment = comment
        self.authors = authors
        self.tournament = tournament
        self.date = date
        self.sources = sources
        self.pass_criteria = pass_criteria

    def getHTMLQuestion(self) -> str:
        text = ''
        textDate = ''
        if self.date:
            textDate = f' от {self.date}'
        if self.tournament:
            t = replaceAngleBrackets(text=self.tournament)
            text += f"<b>Турнир:</b> {t}{textDate}\n"
        q = replaceAngleBrackets(text=self.question)
        q = q.replace("\n",' ')
        q = q.replace('   ',"\n") # Handle question duplet
        text += f"<b>Вопрос:</b> {q}\n"
        return text
    
    def getHTMLAnswer(self) -> str:
        a = replaceAngleBrackets(text=self.answer)
        text = f'<span class="tg-spoiler"><b>Ответ:</b> {a}'+"\n"
        if (self.pass_criteria):
            p = replaceAngleBrackets(text=self.pass_criteria)
            text += f"<b>Зачет:</b> {p}\n"
        if (self.comment):
            c = self.comment.replace("\n",' ')
            c = c.replace('   ',"\n") # Handle question duplet
            c = replaceAngleBrackets(text=c)
            text += f"<b>Комментарий:</b> {c}\n"
        if (self.sources):
            s = replaceAngleBrackets(text=self.sources)
            text += f"<b>Источники:</b> {s}\n"
        text += '</span>'
        return text
    
    def getQuestionPictureUrl(self) -> str:
        return self.__questionPictureUrl

    def getCommentPictureUrl(self) -> str:
        return self.__commentPictureUrl

def removePicture(text) -> str:
    ret = re.sub(pattern=r'\(pic: \d+\.[\w\d]+\)', repl='', string=text)
    ret = ret.strip()
    return ret

def extractPicture(text):
    pics = re.findall(pattern=r'^\(pic: \d+\.[\w\d]+\)', string=text)
    if len(pics)>0:
        p = pics[0]
        ret = re.findall(pattern=r'\d+\.[\w\d]+',string=p)
        if (len(ret)>0):
            return ret[0]
    return None

def getPictureUrl(pictureName) -> str:
    return PICTURE_URL + pictureName

def get_chgk_question() -> None | ChgkQuestion:
    try:
        r = requests.get(url=CHGK_URL)
    except RequestException as e:
        log(str=f"Error during HHTP request: {e}", logLevel=LOG_ERROR)
        return None
    try:
        data = xmltodict.parse(xml_input=r.content)
    except Exception as e:
        log(str=f"Error during xmlparsing: {e}", logLevel=LOG_ERROR)
        return None
    q = data.get('search')
    if (not q):
        log(str=f'Cannot parse URL response: {data}', logLevel=LOG_ERROR)
        return None
    q = q.get('question')
    if (not q):
        log(str=f'Cannot parse URL response 2: {data}', logLevel=LOG_ERROR)
        return None
    qTmp = q.get('Question')
    aTmp = q.get('Answer')
    if (not qTmp or not aTmp):
        log(str=f'Cannot parse URL (no question or answer): {data}', logLevel=LOG_ERROR)
        return None
    # Limit question length
    if (len(qTmp) > MAX_QUESTION_LENGTH):
        qTmp = qTmp[:MAX_QUESTION_LENGTH]
    question = qTmp
    picTmp = extractPicture(text=qTmp)
    questionPicture = None
    if (picTmp):
        log(str=f'Question picture found: {picTmp}', logLevel=LOG_DEBUG)
        questionPicture = getPictureUrl(pictureName=picTmp)
        question = removePicture(text=qTmp)
    answer = aTmp
    cTmp = q.get('Comments')
    comment = cTmp
    commentPicture = None
    if (cTmp):
        picTmp = extractPicture(text=cTmp)
        if (picTmp):
            log(str=f'Comment picture found: {picTmp}', logLevel=LOG_DEBUG)
            commentPicture = getPictureUrl(pictureName=picTmp)
            comment = removePicture(text=cTmp)
    authors = q.get('Authors')
    sources = q.get('Sources')
    tournament = q.get('tournamentTitle')
    date = q.get('tournamentPlayedAt')
    pass_criteria = q.get('passCriteria')
    question = ChgkQuestion(
        question=question,
        answer=answer,
        questionPicture = questionPicture,
        comment=comment,
        commentPicture = commentPicture,
        authors=authors,
        sources=sources,
        tournament=tournament,
        date=date,
        pass_criteria=pass_criteria
    )
    return question

def decodeQuestion(pickle_question) -> ChgkQuestion:
    Q = pickle.loads(pickle_question)
    return Q

def encodeQuestion(Q: ChgkQuestion) -> bytes:
    return pickle.dumps(obj=Q)


def checkCorrectAnswer(correct_answer: str, answer: str) -> bool:
    # Make adjustment first
    correct_answer = adjustText(text=correct_answer)
    answer = adjustText(text=answer)
    # Remove trialing dot
    if (correct_answer[-1] == '.'):
        correct_answer = correct_answer[:-1]
    return isStrSimilar(str1=correct_answer, str2=answer)
