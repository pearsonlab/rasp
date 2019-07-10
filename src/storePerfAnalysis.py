import numpy as np
import matplotlib.pyplot as plt
import os

cwd = os.getcwd()
acquirePut = np.load(cwd + "/perf/AcquirerPut.npy")
analysisPut = np.load(cwd + "/perf/AnalysisPut.npy")
analysisGet = np.load(cwd + "/perf/AnalysisGet.npy")
processPut = np.load(cwd + "/perf/ProcessorPut.npy")
processGet = np.load(cwd + "/perf/ProcessorGet.npy")
visualGet = np.load(cwd + "/perf/VisualGet.npy")

dataList = {
    "AcquirePut": acquirePut,
    "AnalysisPut": analysisPut,
    "AnalysisGet": analysisGet,
    "ProcessPut": processPut,
    "ProcessGet": processGet,
    "VisualGet": visualGet 
}

print(dataList.values)
print(dataList.keys)

fig, axes = plt.subplots(nrows = len(dataList), ncols = 1)
fig.tight_layout()
for i, val, key in zip(range(len(dataList)), dataList.values(), dataList.keys()):
    axes[i].plot(list(range(len(val))), val, marker=".", color="blue", label=key)
    axes[i].set_title(key)
    axes[i].set_xlabel("Obj #")
    axes[i].set_ylabel("Time (s)")

plt.show()
