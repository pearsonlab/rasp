import numpy as np
import matplotlib.pyplot as plt
import os

cwd = os.getcwd()
acquirePut = np.load(cwd + "/perf/AcquirerPut.npy")
analysisPut = np.load(cwd + "/perf/AnalysisPut.npy")
processPut = np.load(cwd + "/perf/ProcessorPut.npy")
processGet = np.load(cwd + "/perf/ProcessorGet.npy")
visualGet = np.load(cwd + "/perf/VisualGet.npy")

dataList = {
    "AcquirePut": acquirePut,
    "AnalysisPut": analysisPut,
    "ProcessPut": processPut,
    "ProcessGet": processGet,
    "VisualGet": visualGet 
}

#test = [12,42,4,2,55,2,2]

print(dataList.values)
print(dataList.keys)

fig, axes = plt.subplots(nrows = 5, ncols = 1)
fig.tight_layout()
for i, val, key in zip(range(len(dataList)), dataList.values(), dataList.keys()):
    #axes[i].plot(list(range(len(dataList.values[i]))), dataList.values[i])
    axes[i].plot(list(range(len(val))), val, marker=".", color="blue", label=key)
    axes[i].set_title(key)
    axes[i].set_xlabel("Obj #")
    axes[i].set_ylabel("Time (s)")

plt.show()
