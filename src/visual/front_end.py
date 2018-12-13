import sys
#sys.path.append('src')
#print(sys.path)
from PyQt5 import QtGui,QtCore
from visual import rasp_ui
from nexus.nexus import Nexus
import numpy as np
import pylab
import time
import pyqtgraph
from threading import Thread
from multiprocessing import Process
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from process.process import CaimanProcessor as cp

import logging; logger = logging.getLogger(__name__)


class FrontEnd(QtGui.QMainWindow, rasp_ui.Ui_MainWindow):

    def __init__(self, parent=None):
    
        pyqtgraph.setConfigOption('background', 'w') #before loading widget
        super(FrontEnd, self).__init__(parent)
        
        self.setupUi(self)
        
        self.nexus = Nexus('NeuralNexus')
        self.nexus.createNexus()

        #temp
        #self.proc = cp.setupProcess(self.nexus.Processor, 'params_dict')
        
        self.nexus.setupProcessor()

        self.pushButton_3.clicked.connect(_call(self._runProcess))
        self.pushButton_3.clicked.connect(_call(self.update))
        self.pushButton.clicked.connect(_call(self._loadParams))
    
    
    def _loadParams(self):
        ''' Button event to load parameters from file
            File location determined from user input
            Throws FileNotFound error
        '''
        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')
            #TODO: make default home folder system-independent
        try:
            self.nexus.loadTweak(fname[0])
        except FileNotFoundError as e:
            logger.error('File not found {}'.format(e))
            raise FileNotFoundError
    
    
    def _runProcess(self):
        #fnames = self.proc.client.get('params_dict')['fnames'] #CHANGEME
        #output = 'outputEstimates'
        self.t = Thread(target=self.nexus.runProcessor)
        self.t.daemon = True
        self.t.start()

        #TODO: grey out button until self.t is done, but allow other buttons to be active

        #self.p = Process(target=self.nexus.runProcessor)
        #self.p.start()
        #self.p.join()

        #cp.runProcess(self.proc, fnames, output) #TODO: need flag for multiple updates...


    def update(self):

        num = 0
        try:
            whereEst = self.nexus.Processor.getStored()['params_dict']['ouput']
            self.ests = self.nexus.limbo.get(whereEst)
            #print('got it', self.ests)
            a, b = self.ests.shape
            num+=1
            print(num)
        except Exception as e:
            logger.info('output does not yet exist. error: {}'.format(e))

        t1=time.clock()
        points=100 #number of data points
        X=np.arange(points)
        Y=np.sin(np.arange(points)/points*3*np.pi+time.time())
        C=pyqtgraph.hsvColor(time.time()/5%1,alpha=.5)
        pen=pyqtgraph.mkPen(color=C,width=10)
        self.grplot.plot(X,Y,pen=pen,clear=True)
        
        if self.checkBox.isChecked():
            QtCore.QTimer.singleShot(1, self.update)


    def closeEvent(self, event):

        confirm = QMessageBox.question(self, 'Message', 'Quit without saving?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.nexus.destroyNexus()
            event.accept()
        else: event.ignore()


def _call(fnc, *args, **kwargs):
    ''' Call handler for (external) events
    '''
    
    def _callback():
        return fnc(*args, **kwargs)
    return _callback


if __name__=="__main__":
    app = QtGui.QApplication(sys.argv)
    rasp = FrontEnd()
    rasp.show()
    #rasp.update() #start with something in plot
    app.exec_()
