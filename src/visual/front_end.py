import sys
from PyQt5 import QtGui,QtCore
from PyQt5.QtGui import QColor
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
        ''' Setup GUI
            Setup and start Nexus
        '''
        pyqtgraph.setConfigOption('background', QColor(229, 229, 229)) #before loading widget
        super(FrontEnd, self).__init__(parent)
        
        self.setupUi(self)
        self.setStyleSheet("QMainWindow {background: 'white';}")
                
        self.rawplot.ui.histogram.hide()
        self.rawplot.ui.roiBtn.hide()
        self.rawplot.ui.menuBtn.hide()
        self.checkBox.setChecked(True)

        #init line plot
        self.c1 = self.grplot.plot()
        self.c2 = self.grplot_2.plot()
        self.c3 = self.grplot_3.plot()
        grplot = [self.grplot, self.grplot_2, self.grplot_3]
        for plt in grplot:
            plt.getAxis('bottom').setTickSpacing(major=50, minor=50)
            plt.setLabel('bottom', "Frames")
            plt.setLabel('left', "Temporal traces")
        # self.grplot_3.getAxis('bottom').setTickSpacing(major=50, minor=50)
        # self.grplot_3.setLabel('bottom', "Frames")
        # self.grplot_3.setLabel('left', "Temporal traces")
        self.updateLines()
        
        self.nexus = Nexus('NeuralNexus')
        self.nexus.createNexus()

        #Currently running initialize here        
        self.nexus.setupProcessor()

        self.pushButton_3.clicked.connect(_call(self._runProcess))
        self.pushButton_3.clicked.connect(_call(self.update))
        self.pushButton.clicked.connect(_call(self._loadParams))
        self.checkBox.stateChanged.connect(self.update) #TODO: call outside process or restric to checkbox update
    
    
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
            #raise FileNotFoundError
    
    
    def _runProcess(self):
        '''Run ImageProcessor in separate thread
        '''
        self.t = Thread(target=self.nexus.runProcessor)
        self.t.daemon = True
        self.t.start()

        #TODO: grey out button until self.t is done, but allow other buttons to be active


    def update(self):
        ''' Update visualization while running
        '''

        self.updateLines()

        #plot video
        image = None
        try:
            image = self.nexus.getPlotRaw()
        except Exception as e:
            logger.error('Oh no {0}'.format(e))

        if image is not None:
            self.rawplot.setImage(image.T)

        #re-update
        if self.checkBox.isChecked():
            QtCore.QTimer.singleShot(150, self.update)

    def updateLines(self):
        ''' Helper function to plot the line traces
            of the activity of the selected neurons.
        '''
        #plot traces
        pen=pyqtgraph.mkPen(width=2, color='r')
        pen2=pyqtgraph.mkPen(width=2, color='b')
        pen3=pyqtgraph.mkPen(width=2, color='g')
        Y = None
        try:
            #self.ests = self.nexus.getEstimates()
            (X, Y) = self.nexus.getPlotEst()
        except Exception as e:
            logger.error('output does not yet exist. error: {}'.format(e))

        if(Y is not None):
            self.c1.setData(X, Y[0], pen=pen)
            self.c2.setData(X, Y[1], pen=pen2)
            self.c3.setData(X, Y[2], pen=pen3)

    def closeEvent(self, event):
        '''Clicked x/close on window
            Add confirmation for closing without saving
        '''
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
    app.exec_()
