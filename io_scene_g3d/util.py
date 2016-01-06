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

# Global rounding factor for floats
FLOAT_ROUND = 6
ROUND_STRING = "%" + str(FLOAT_ROUND + 3) + "." + str(FLOAT_ROUND) + "f"

_DEBUG_ = 3
_WARN_ = 2
_ERROR_ = 1

LOG_LEVEL = _ERROR_
# LOG_LEVEL = _WARN_
# LOG_LEVEL = _DEBUG_


class Util(object):

    def compareVector(self, v1, v2):
        a1 = [ROUND_STRING % v1[0], ROUND_STRING % v1[1], ROUND_STRING % v1[2]]
        a2 = [ROUND_STRING % v2[0], ROUND_STRING % v2[1], ROUND_STRING % v2[2]]
        return a1 == a2

    def compareQuaternion(self, q1, q2):
        a1 = [ROUND_STRING % q1[0], ROUND_STRING % q1[1], ROUND_STRING % q1[2], ROUND_STRING % q1[3]]
        a2 = [ROUND_STRING % q2[0], ROUND_STRING % q2[1], ROUND_STRING % q2[2], ROUND_STRING % q2[3]]
        return a1 == a2

    def floatToString(self, floatNumber):
        return ROUND_STRING % floatNumber

    def limitFloatPrecision(self, floatNumber):
        return float(round(floatNumber, FLOAT_ROUND))

    def limitFloatListPrecision(self, listOfFloats):
        newList = [None] * len(listOfFloats)
        for i in range(0, len(listOfFloats)):
            newList[i] = float(round(listOfFloats[i], FLOAT_ROUND))

        return newList

    # ## DEBUG METHODS ###

    def debug(self, message):
        if LOG_LEVEL >= _DEBUG_:
            print("[DEBUG] %s" % message)

    def warn(self, message):
        if LOG_LEVEL >= _WARN_:
            print("[WARN] %s" % message)

    def error(self, message):
        if LOG_LEVEL >= _ERROR_:
            print("[ERROR] %s" % message)
