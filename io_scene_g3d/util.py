# Global rounding factor for floats
FLOAT_ROUND = 6
ROUND_STRING = "%" + str(FLOAT_ROUND+3) + "." + str(FLOAT_ROUND) + "f"

_DEBUG_ = 3
_WARN_ = 2
_ERROR_ = 1

#LOG_LEVEL = _WARN_
LOG_LEVEL = _DEBUG_

class Util(object):
    def compareVector(self, v1, v2):
        a1 = [ ROUND_STRING % v1[0] , ROUND_STRING % v1[1] , ROUND_STRING % v1[2] ]
        a2 = [ ROUND_STRING % v2[0] , ROUND_STRING % v2[1] , ROUND_STRING % v2[2] ]
        return a1 == a2
    
    def compareQuaternion(self, q1, q2):
        a1 = [ ROUND_STRING % q1[0] , ROUND_STRING % q1[1] , ROUND_STRING % q1[2] , ROUND_STRING % q1[3] ]
        a2 = [ ROUND_STRING % q2[0] , ROUND_STRING % q2[1] , ROUND_STRING % q2[2] , ROUND_STRING % q2[3] ]
        return a1 == a2
    
    def floatToString(self, floatNumber):
        return ROUND_STRING % floatNumber
            
    ### DEBUG METHODS ###
    
    def debug(self, message):
        if LOG_LEVEL >= _DEBUG_: print("[DEBUG] %s" % message)
    
    def warn(self, message):
        if LOG_LEVEL >= _WARN_: print("[WARN] %s" % message)

    def error(self, message):
        if LOG_LEVEL >= _ERROR_: print("[ERROR] %s" % message)