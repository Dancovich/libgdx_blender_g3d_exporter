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

import time
prof = {}


class profile:
    '''Function decorator for code profiling.'''

    def __init__(self, name):
        self.name = name

    def __call__(self, fun):
        def profile_fun(*args, **kwargs):
            start = time.clock()
            try:
                return fun(*args, **kwargs)
            finally:
                duration = time.clock() - start
                if fun not in prof:
                    prof[fun] = [self.name, duration, 1]
                else:
                    prof[fun][1] += duration
                    prof[fun][2] += 1
        return profile_fun


def print_stats():
    '''Prints profiling results to the console. Run from a Python controller.'''

    def timekey(stat):
        return stat[1] / float(stat[2])
    stats = sorted(prof.values(), key=timekey, reverse=True)

    print('=== Execution Statistics ===')
    print('Times are in milliseconds.')
    print('{:<55} {:>6} {:>7} {:>6}'.format('FUNCTION', 'CALLS', 'SUM(ms)', 'AV(ms)'))
    for stat in stats:
        print('{:<55} {:>6} {:>7.0f} {:>6.2f}'.format(
            stat[0], stat[2],
            stat[1] * 1000,
            (stat[1] / float(stat[2])) * 1000))
