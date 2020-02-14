"""
Created on Aug 28, 2018

@author: mjasnik
"""

# import section
import dbus

# timekpr imports
from timekpr.common.constants import constants as cons
from timekpr.common.log import log
from timekpr.common.utils import misc


class timekprUserManager(object):
    """A connection with login1"""

    def __init__(self, pLog, pUserName, pUserPathOnBus):
        """Initialize manager"""
        # init logging firstly
        log.setLogging(pLog)

        # save the bus and user
        self._timekprBus = dbus.SystemBus()
        self._userName = pUserName

        # dbus performance measurement
        misc.measureTimeElapsed(pStart=True)

        # get dbus object
        self._login1UserObject = self._timekprBus.get_object(cons.TK_DBUS_L1_OBJECT, pUserPathOnBus)
        # measurement logging
        log.log(cons.TK_LOG_LEVEL_INFO, "PERFORMANCE (DBUS) - acquiring \"%s\" took too long (%is)" % (cons.TK_DBUS_L1_OBJECT, misc.measureTimeElapsed(pResult=True))) if misc.measureTimeElapsed(pStop=True) >= cons.TK_DBUS_ANSWER_TIME else True

        # get dbus interface for properties
        self._login1UserInterface = dbus.Interface(self._login1UserObject, cons.TK_DBUS_PROPERTIES_INTERFACE)
        # measurement logging
        log.log(cons.TK_LOG_LEVEL_INFO, "PERFORMANCE (DBUS) - acquiring \"%s\" took too long (%is)" % (cons.TK_DBUS_PROPERTIES_INTERFACE, misc.measureTimeElapsed(pResult=True))) if misc.measureTimeElapsed(pStop=True) >= cons.TK_DBUS_ANSWER_TIME else True

        # user usersessions
        self._timekprUserSessions = {}

    def cacheUserSessionList(self):
        """Determine user sessions and cache session objects for further reference."""
        log.log(cons.TK_LOG_LEVEL_DEBUG, "---=== start cacheUserSessionList for \"%s\" ===---" % (self._userName))
        # dbus performance measurement
        misc.measureTimeElapsed(pStart=True)
        # get all user sessions
        userSessions = self._login1UserInterface.Get(cons.TK_DBUS_USER_OBJECT, "Sessions")
        # measurement logging
        log.log(cons.TK_LOG_LEVEL_INFO, "PERFORMANCE (DBUS) - getting sessions for \"%s\" took too long (%is)" % (cons.TK_DBUS_USER_OBJECT, misc.measureTimeElapsed(pResult=True))) if misc.measureTimeElapsed(pStop=True) >= cons.TK_DBUS_ANSWER_TIME else True

        log.log(cons.TK_LOG_LEVEL_DEBUG, "got %i sessions, start loop" % (len(userSessions)))
        log.log(cons.TK_LOG_LEVEL_EXTRA_DEBUG, str(userSessions))

        # init active sessions
        activeSessions = {}

        # go through all user sessions
        for userSession in userSessions:
            # sessionId & sessionPath on dbus
            sessionId = str(userSession[0])
            sessionPath = str(userSession[1])
            # save active sessions
            activeSessions[sessionId] = 0

            # if we have not yet saved a user session, let's do that to improve interaction with dbus
            if sessionId not in self._timekprUserSessions:
                log.log(cons.TK_LOG_LEVEL_DEBUG, "adding session: %s" % (sessionId))
                # dbus performance measurement
                misc.measureTimeElapsed(pStart=True)

                # get object and interface to save it
                sessionObject = self._timekprBus.get_object(cons.TK_DBUS_L1_OBJECT, sessionPath)
                # measurement logging
                log.log(cons.TK_LOG_LEVEL_INFO, "PERFORMANCE (DBUS) - acquiring \"%s\" took too long (%is)" % (cons.TK_DBUS_L1_OBJECT, misc.measureTimeElapsed(pResult=True))) if misc.measureTimeElapsed(pStop=True) >= cons.TK_DBUS_ANSWER_TIME else True

                # get object and interface to save it
                sessionInterface = dbus.Interface(sessionObject, cons.TK_DBUS_PROPERTIES_INTERFACE)
                # measurement logging
                log.log(cons.TK_LOG_LEVEL_INFO, "PERFORMANCE (DBUS) - acquiring \"%s\" took too long (%is)" % (cons.TK_DBUS_PROPERTIES_INTERFACE, misc.measureTimeElapsed(pResult=True))) if misc.measureTimeElapsed(pStop=True) >= cons.TK_DBUS_ANSWER_TIME else True

                # cache sessions
                self._timekprUserSessions[sessionId] = {cons.TK_CTRL_DBUS_SESS_OBJ: sessionObject, cons.TK_CTRL_DBUS_SESS_IF: sessionInterface, cons.TK_CTRL_DBUS_SESS_PROP: {}}

                # add static properties
                self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_PROP]["Type"] = str(sessionInterface.Get(cons.TK_DBUS_SESSION_OBJECT, "Type"))
                self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_PROP]["VTNr"] = str(int(sessionInterface.Get(cons.TK_DBUS_SESSION_OBJECT, "VTNr")))
                self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_PROP]["Seat"] = str(sessionInterface.Get(cons.TK_DBUS_SESSION_OBJECT, "Seat")[0])
            else:
                log.log(cons.TK_LOG_LEVEL_DEBUG, "session already cached: %s" % (sessionId))

        # list of sessions to delete
        removableSesssions = {}

        # collect sessions not on the list
        for userSession in self._timekprUserSessions:
            # user session is not found
            if userSession not in activeSessions:
                removableSesssions[userSession] = 0

        # get rid of sessions not on the list
        for userSession in removableSesssions:
            log.log(cons.TK_LOG_LEVEL_DEBUG, "removing session: %s" % (userSession))
            self._timekprUserSessions.pop(userSession)

        log.log(cons.TK_LOG_LEVEL_DEBUG, "---=== finish cacheUserSessionList for \"%s\" ===---" % (self._userName))

    def isUserActive(self, pSessionTypes, pTrackInactive):
        """Check if user is active."""
        log.log(cons.TK_LOG_LEVEL_DEBUG, "---=== start isUserActive for \"%s\" ===---" % (self._userName))
        log.log(cons.TK_LOG_LEVEL_DEBUG, "supported session types: %s" % (str(pSessionTypes)))

        # get all user sessions
        userState = str(self._login1UserInterface.Get(cons.TK_DBUS_USER_OBJECT, "State"))
        userIdleState = str(bool(self._login1UserInterface.Get(cons.TK_DBUS_USER_OBJECT, "IdleHint")))
        log.log(cons.TK_LOG_LEVEL_DEBUG, "user stats, state: %s, idleState: %s" % (userState, userIdleState))

        # cache sessions
        self.cacheUserSessionList()

        # to determine if user is active for all sessions:
        #    session must not be "active"
        #    idlehint must be true
        #    special care must be taken for tty sessions

        # init active sessions
        userActive = False

        # go through all user sessions
        for sessionId in self._timekprUserSessions:
            # dbus performance measurement
            misc.measureTimeElapsed(pStart=True)

            # get needed static properties
            sessionType = self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_PROP]["Type"]
            sessionVTNr = self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_PROP]["VTNr"]
            # get needed properties
            sessionState = str(self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_IF].Get(cons.TK_DBUS_SESSION_OBJECT, "State"))
            sessionIdleState = str(bool(self._timekprUserSessions[sessionId][cons.TK_CTRL_DBUS_SESS_IF].Get(cons.TK_DBUS_SESSION_OBJECT, "IdleHint")))

            # measurement logging
            log.log(cons.TK_LOG_LEVEL_INFO, "PERFORMANCE (DBUS) - property get for session \"%s\" took too long (%is)" % (sessionId, misc.measureTimeElapsed(pResult=True))) if misc.measureTimeElapsed(pStop=True) >= cons.TK_DBUS_ANSWER_TIME else True

            log.log(cons.TK_LOG_LEVEL_DEBUG, "got session - type: %s, VTNr: %s, state: %s, idle: %s" % (sessionType, sessionVTNr, sessionState, sessionIdleState))

            # check if active
            if sessionState == "active" and sessionIdleState == "False":
                log.log(cons.TK_LOG_LEVEL_DEBUG, "session %s active" % (sessionId))

                # validate against session types we manage
                if sessionType not in pSessionTypes:
                    # session is not on the list of session types we track
                    log.log(cons.TK_LOG_LEVEL_DEBUG, "    session %s excluded (thus effectively inactive)" % (sessionId))
                else:
                    # session is on the list of session types we track and session is active
                    userActive = True
            elif sessionType in pSessionTypes:
                # user is not active
                log.log(cons.TK_LOG_LEVEL_DEBUG, "session %s inactive" % (sessionId))

                # if we track inactive
                if pTrackInactive:
                    # we track inactive sessions
                    userActive = True

                    # session is not on the list of session types we track
                    log.log(cons.TK_LOG_LEVEL_DEBUG, "    session %s included as active (we track inactive sessions)" % (sessionId))
            else:
                # session is not on the list of session types we track
                log.log(cons.TK_LOG_LEVEL_DEBUG, "session %s not tracked" % (sessionId))

        log.log(cons.TK_LOG_LEVEL_DEBUG, "---=== finish isUserActive: %s ===---" % (str(userActive)))

        # return whether user is active
        return userActive
