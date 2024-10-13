import requests
from requests.exceptions import RequestException, JSONDecodeError
import xmltodict
import pickle
from log_lib import *
from db_lib import *
from neo_common_lib import *

CHGK_URL = "https://db.chgk.info/xml/random/answers/types1/912864593/limit1"

MIN_SIMILARITY = 3

def isStrSimilar(str1,str2) -> bool:
    dist = getStrDistance(str1=str1,str2=str2)
    return dist <= MIN_SIMILARITY

##############################
class ChgkQuestion:
    def __init__(self, question, answer, pic=None, comment=None, authors=None, tournament=None, date=None, sources=None) -> None:
        self.question = question
        self.answer = answer
        self.pic = pic
        self.comment = comment
        self.authors = authors
        self.tournament = tournament
        self.date = date
        self.sources = sources

def get_chgk_question() -> None | ChgkQuestion:
    try:
        r = requests.get(url=CHGK_URL)
        data = xmltodict.parse(xml_input=r.content)
    except RequestException as e:
        log(str=f"Error during HHTP request: {e}", logLevel=LOG_ERROR)
        return None
    q = data.get('search')
    if (not q):
        log(str=f'Cannot parse URL response: {data}', logLevel=LOG_ERROR)
        return None
    q = q.get('question')
    if (not q):
        log(str=f'Cannot parse URL response 2: {data}', logLevel=LOG_ERROR)
        return None
    question = q.get('Question')
    answer = q.get('Answer')
    if (not question or not answer):
        log(str=f'Cannot parse URL (no question or answer): {data}', logLevel=LOG_ERROR)
        return None
    comment = q.get('Comments')
    authors = q.get('Authors')
    sources = q.get('Sources')
    tournament = q.get('tournamentTitlernament')
    date = q.get('tournamentPlayedAt')
    question = ChgkQuestion(
        question=question,
        answer=answer,
        pic = '',
        comment=comment,
        authors=authors,
        sources=sources,
        tournament=tournament,
        date=date

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
