# pip install julia si_prefix

import sys
import time
from functools import wraps

import numpy as np
from si_prefix import si_format

scale = 6
iterations = 1000

# Initializes PyJulia
print('Initializing Julia. Takes ~30 sec.')
from julia.api import Julia
jl = Julia(compiled_modules=False) # See https://pyjulia.readthedocs.io/en/latest/troubleshooting.html#your-python-interpreter-is-statically-linked-to-libpython

from julia import Main  # Loads main Julia interface
Main.eval(f'scale = {scale}')
Main.include('benchmark_tools.jl')  # Run file to add functions to namespace

def timethis(n):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            t = np.zeros(n, dtype=np.float64)
            for i in range(n):
                start = time.time()
                func(*args, **kwargs)
                t[i] = time.time() - start
            return t
        return wrapper
    return decorate

# Define things to be transferred
r = [np.random.random((10,10,10**i)) for i in range(scale)]

# Define functions
to_julia = lambda i: Main.eval('to_julia')(r[i])
to_julia.__name__ = 'to_julia'
to_julia_zero_copy = lambda i: Main.eval('pyfunction(to_julia, PyArray)')(r[i])
to_julia_zero_copy.__name__ = 'to_julia_zero_copy'

from_julia = Main.eval('from_julia')
bidirectional_zero_copy = Main.eval('pyfunction(bidirectional, PyArray)')
bidirectional = Main.eval('bidirectional')

all_time = list()

def julia_benchmark(funclist, iterations=iterations):
    print(f'Starting benchmark. Running for {iterations} iterations spanning {scale} orders of magnitude.\n')
    # Compile
    for func in funclist:
        for i in range(1, scale):
            func(i)
    
    for func in funclist:
        for i in range(1, scale):
            t = timethis(iterations)(func)(i)
            p = np.percentile(t, [5, 95])
            all_time.append(t)
            print(f'{func.__name__} ({si_format(sys.getsizeof(r[i]))}B): Percentiles 5th: {si_format(p[0])}s, 95th: {si_format(p[1])}s')
        print()
    
    print(f'Checking for faithful transfer.')
    for i in range(1, scale):
        assert np.array_equal(r[i], bidirectional(r[i]))
        assert np.array_equal(r[i], bidirectional_zero_copy(r[i]))
    
    print(f'OK')
    print(f'\nAll done.')

if __name__ == '__main__':
    julia_benchmark([from_julia, to_julia, to_julia_zero_copy])

# Data analysis and plot
#
# import pandas as pd
# size = len(all_time[0])
# scale = size * [80128] + size * [800128] + size * [8000128] + size * [8000128] + size * [80000128]
#
# df1 = pd.DataFrame(columns=['scale', 'name', 'time'])
# df1['scale'] = scale
# df1['name'] = ['from_julia'] * 5000
# df1['time'] = np.concatenate(all_time[0:5])
# df1 = df1.drop(0)
#
# df2 = pd.DataFrame(columns=['scale', 'name', 'time'])
# df2['scale'] = scale
# df2['name'] = ['to_julia'] * 5000
# df2['time'] = np.concatenate(all_time[5:10])
#
# df3 = pd.DataFrame(columns=['scale', 'name', 'time'])
# df3['scale'] = scale
# df3['name'] = ['to_julia_zero_copy'] * 5000
# df3['time'] = np.concatenate(all_time[10:15])
#
# final = pd.concat([df1, df2, df3])
#
# sns.set(font_scale=1.3)
# plt.figure(figsize=(12, 9), dpi=300)
# ax = sns.lineplot(x='scale', y='time', hue='name', data=final, ci=95, markers=True)
# ax.set(xscale='log', yscale='log', ylabel='log time (s)', xlabel='Bytes')
# sns.despine(left=True)