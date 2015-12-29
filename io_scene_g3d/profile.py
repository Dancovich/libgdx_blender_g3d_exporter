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
                if not fun in prof:
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