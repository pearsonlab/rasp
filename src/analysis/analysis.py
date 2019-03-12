import logging; logger = logging.getLogger(__name__)


class Analysis():
    '''Abstract class for the analysis module
    Performs additional computations on the extracted
    neural activity from the processor module
    '''
    def setup(self):
        # Essenitally the registration process
        raise NotImplementedError

    def run(self):
        # Get activity and then do additional computations on estimates
        raise NotImplementedError
    
    def putAnalysis(self):
        # Update the DS with estimates
        raise NotImplementedError


class MeanAnalysis(Analysis):
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.ests = None

    def setup(self):
        pass

    def run(self, ests):
        # ests structure: np.array([components, frames])
        pass

    def runAvg(self, ests):
        estsAvg = []
        for i in range(ests.shape[0]):
            tmpList = []
            for j in range(int(np.floor(ests.shape[1]/100))+1):
                tmp = np.mean(ests[int(i)][int(j)*100:int(j)*100+100])
                tmpList.append(tmp)
            estsAvg.append(tmpList)
        self.estsAvg = np.array(estsAvg)
        
        return self.estsAvg

    def putAnalysis(self):
        pass
