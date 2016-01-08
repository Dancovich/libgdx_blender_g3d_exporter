#################################################################################
# Copyright 2014 See AUTHORS file.
#
# Licensed under the GNU General Public License Version 3.0 (the "LICENSE");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.gnu.org/licenses/gpl-3.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#################################################################################

# <pep8 compliant>

from math import fabs

# Global rounding factor for floats
FLOAT_ROUND = 6
ROUND_STRING = "%" + str(FLOAT_ROUND + 3) + "." + str(FLOAT_ROUND) + "f"

_DEBUG_ = 3
_WARN_ = 2
_ERROR_ = 1

LOG_LEVEL = _ERROR_
# LOG_LEVEL = _WARN_
# LOG_LEVEL = _DEBUG_

# Sorts vertex attributes
_ATTRIBUTE_SORT_ = {}
_ATTRIBUTE_SORT_['POSITION'] = 10
_ATTRIBUTE_SORT_['NORMAL'] = 20
_ATTRIBUTE_SORT_['TANGENT'] = 30
_ATTRIBUTE_SORT_['BINORMAL'] = 40
_ATTRIBUTE_SORT_['COLOR'] = 50
_ATTRIBUTE_SORT_['COLORPACKED'] = 60
_ATTRIBUTE_SORT_['TEXCOORD0'] = 70
_ATTRIBUTE_SORT_['TEXCOORD1'] = 71
_ATTRIBUTE_SORT_['TEXCOORD2'] = 72
_ATTRIBUTE_SORT_['TEXCOORD3'] = 73
_ATTRIBUTE_SORT_['TEXCOORD4'] = 74
_ATTRIBUTE_SORT_['TEXCOORD5'] = 75
_ATTRIBUTE_SORT_['TEXCOORD6'] = 76
_ATTRIBUTE_SORT_['TEXCOORD7'] = 77
_ATTRIBUTE_SORT_['TEXCOORD8'] = 78
_ATTRIBUTE_SORT_['TEXCOORD9'] = 79
_ATTRIBUTE_SORT_['BLENDWEIGHT0'] = 80
_ATTRIBUTE_SORT_['BLENDWEIGHT1'] = 81
_ATTRIBUTE_SORT_['BLENDWEIGHT2'] = 82
_ATTRIBUTE_SORT_['BLENDWEIGHT3'] = 83
_ATTRIBUTE_SORT_['BLENDWEIGHT4'] = 84
_ATTRIBUTE_SORT_['BLENDWEIGHT5'] = 85
_ATTRIBUTE_SORT_['BLENDWEIGHT6'] = 86
_ATTRIBUTE_SORT_['BLENDWEIGHT7'] = 87
_ATTRIBUTE_SORT_['BLENDWEIGHT8'] = 88
_ATTRIBUTE_SORT_['BLENDWEIGHT9'] = 89


def attributeSort(attribute):
    return 0 if attribute is None else _ATTRIBUTE_SORT_[attribute.name]


class Util(object):

    @staticmethod
    def compareVector(v1, v2):
        a1 = [ROUND_STRING % v1[0], ROUND_STRING % v1[1], ROUND_STRING % v1[2]]
        a2 = [ROUND_STRING % v2[0], ROUND_STRING % v2[1], ROUND_STRING % v2[2]]
        return a1 == a2

    @staticmethod
    def compareQuaternion(q1, q2):
        a1 = [ROUND_STRING % q1[0], ROUND_STRING % q1[1], ROUND_STRING % q1[2], ROUND_STRING % q1[3]]
        a2 = [ROUND_STRING % q2[0], ROUND_STRING % q2[1], ROUND_STRING % q2[2], ROUND_STRING % q2[3]]
        return a1 == a2

    @staticmethod
    def floatToString(floatNumber):
        if round(floatNumber, FLOAT_ROUND) != 0.0:
            return ROUND_STRING % floatNumber
        else:
            return ROUND_STRING % fabs(floatNumber)
    
    @staticmethod
    def floatListToString(floatList):
        if floatList is None:
            return None
        
        newList = [None] * len(floatList)
        for i in range(0, len(floatList)):
            newList[i] = ROUND_STRING % floatList[i]
        return newList

    @staticmethod
    def limitFloatPrecision(floatNumber):
        return float(round(floatNumber, FLOAT_ROUND))

    @staticmethod
    def limitFloatListPrecision(listOfFloats):
        newList = [None] * len(listOfFloats)
        for i in range(0, len(listOfFloats)):
            newList[i] = float(round(listOfFloats[i], FLOAT_ROUND))

        return newList

    # ## DEBUG METHODS ###

    @staticmethod
    def debug(message):
        if LOG_LEVEL >= _DEBUG_:
            print("[DEBUG] %s" % message)

    @staticmethod
    def warn(message):
        if LOG_LEVEL >= _WARN_:
            print("[WARN] %s" % message)

    @staticmethod
    def error(message):
        if LOG_LEVEL >= _ERROR_:
            print("[ERROR] %s" % message)
