from typing import Literal
from neo_common_lib import *
from db_lib import *
from log_lib import *
from NeoChgkBot import *

#===============
# Main section
#---------------
def main() -> Literal[0]:
    initLog()
    TESTCONNECTION = isTestDB()
    log(str=f'Test DB = {TESTCONNECTION}',logLevel=LOG_DEBUG)
    Connection.initConnection(test=TESTCONNECTION)
    bot = NeoChgkBot()
    if (not NeoChgkBot.isInitialized()):
        log(str=f'Error initializing bot. Exiting...')
        exit(code=1)
    # Start bot
    bot.startBot()
    Connection.closeConnection()
    closeLog()
    return 0

if __name__ == "__main__":
    main()
