from os import getenv
from Levenshtein import distance
from dotenv import load_dotenv
from log_lib import *

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

ENV_BOTTOKEN = 'BOTTOKEN'
ENV_BOTTOKENTEST = 'BOTTOKENTEST'

ENV_TESTDB = 'TESTDB'
ENV_TESTBOT = 'TESTBOT'

MIN_SIMILARITY = 3

def isStrSimilar(str1,str2) -> bool:
    dist = getStrDistance(str1=str1,str2=str2)
    return dist <= MIN_SIMILARITY

def getStrDistance(str1, str2) -> int:
    return distance(s1=str1, s2=str2)

def isTestBot() -> bool:
    load_dotenv()
    ret = True # By default
    testbot = getenv(key=ENV_TESTBOT)
    if (testbot):
        if (testbot == "False"):
            ret = False
    return ret

def isTestDB() -> bool:
    load_dotenv()
    ret = True # By default
    testdb = getenv(key=ENV_TESTDB)
    if (testdb):
        if (testdb == "False"):
            ret = False
    return ret    

def getBotToken():
    load_dotenv()
    test = isTestBot()
    if (test):
        token = getenv(key=ENV_BOTTOKENTEST)
    else:
        token = getenv(key=ENV_BOTTOKEN)
    return token

def getDBbConnectionData():
    load_dotenv()
    data={}
    data['dbhost']=getenv(key=ENV_DBHOST)
    data['dbport']=getenv(key=ENV_DBPORT)
    data['dbname']=getenv(key=ENV_DBNAME)
    data['dbuser']=getenv(key=ENV_DBUSER)
    data['dbtoken']=getenv(key=ENV_DBTOKEN)
    for v in data.values():
        if (v == None): # Something wrong
            return None
    return data

def getDBbTestConnectionData():
    load_dotenv()
    data={}
    data['dbhost']=getenv(ENV_DBTESTHOST)
    data['dbport']=getenv(ENV_DBTESTPORT)
    data['dbname']=getenv(ENV_DBTESTNAME)
    data['dbuser']=getenv(ENV_DBTESTUSER)
    data['dbtoken']=getenv(ENV_DBTESTTOKEN)
    for v in data.values():
        if (v == None): # Something wrong
            return None
    return data

# Transofrm str to int
# Returns:
#   int i - if correct it
#   False - if cannot transform
def myInt(str):
    try:
        iYear = int(str)
    except:
        return False
    return iYear

def adjustText(text:str) -> str:
    if (not text):
        return text
    text = text.lower()
    text = text.replace('ё','е') # Replace 'ё'ё
    text = text.replace('ё','е') # Replace 'ё' another ё
    text = text.replace('й','й') # Replace 'й'
    return text

def replaceAngleBrackets(text:str) -> str:
    if (not text):
        return text
    text = text.replace('<','&lt;')
    text = text.replace('>','&gt;')
    return text
