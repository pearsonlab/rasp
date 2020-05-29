import numpy as np

x= np.loadtxt('putAnalysis_time.txt')

tot_times= np.sum(x, axis=0)

avg_time= tot_times/len(x)

print(avg_time)

np.savetxt('test_times/update_original', avg_time)