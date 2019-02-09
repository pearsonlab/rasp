import sys
import os
from PyQt5 import QtGui,QtCore
from PyQt5.QtGui import QColor
from visual import rasp_ui_large
from nexus.nexus import Nexus
import numpy as np
import pylab
import time
import pyqtgraph
from pyqtgraph import EllipseROI, PolyLineROI
from threading import Thread
from multiprocessing import Process
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from process.process import CaimanProcessor as cp

import logging; logger = logging.getLogger(__name__)


class FrontEnd(QtGui.QMainWindow, rasp_ui_large.Ui_MainWindow):

    def __init__(self, parent=None):
        ''' Setup GUI
            Setup and start Nexus
        '''
        pyqtgraph.setConfigOption('background', QColor(100, 100, 100)) #229, 229, 229)) #before loading widget
        super(FrontEnd, self).__init__(parent)
        
        self.setupUi(self)
        pyqtgraph.setConfigOptions(leftButtonPan=False) #TODO: how?
        #self.setStyleSheet("QMainWindow {background: 'white';}")
                
        #self.rawplot.ui.histogram.hide()
        #self.rawplot.ui.roiBtn.hide()
        #self.rawplot.ui.menuBtn.hide()

        # self.raw2View = self.rawplot_2.addPlot()
        # self.raw2View.setAspectLocked(True)
        # print('----------------', type(self.raw2View))
        # self.raw2 = pyqtgraph.ImageItem()
        # self.raw2View.addItem(self.raw2)

        self.customizePlots()
        
        self.nexus = Nexus('NeuralNexus')
        self.nexus.createNexus()

        #Currently running initialize here        
        self.nexus.setupProcessor()
        cwd = os.getcwd()
        self.nexus.setupAcquirer(cwd+'/data/Tolias_mesoscope_1.hdf5')

        self.pushButton_3.clicked.connect(_call(self._runProcess))
        self.pushButton_3.clicked.connect(_call(self.update))
        self.pushButton.clicked.connect(_call(self._loadParams))
        self.checkBox.stateChanged.connect(self.update) #TODO: call outside process or restric to checkbox update
        self.rawplot_2.getImageItem().mouseClickEvent = self.mouseClick

    def customizePlots(self):
        #self.rawplot.ui.histogram.hide()
        #self.rawplot.ui.roiBtn.hide()
        #self.rawplot.ui.menuBtn.hide()

        # self.raw2View = self.rawplot_2.addPlot()
        # self.raw2View.setAspectLocked(True)
        # print('----------------', type(self.raw2View))
        # self.raw2 = pyqtgraph.ImageItem()
        # self.raw2View.addItem(self.raw2)

        self.checkBox.setChecked(True)

        #init line plot
        self.flag = True

        self.c1 = self.grplot.plot(clipToView=True)
        self.c2 = self.grplot_2.plot()
        grplot = [self.grplot, self.grplot_2]
        for plt in grplot:
        #    plt.hideAxis('left')
        #    plt.hideAxis('bottom')
            plt.getAxis('bottom').setTickSpacing(major=50, minor=50)
        #    plt.setLabel('bottom', "Frames")
        #    plt.setLabel('left', "Temporal traces")
        self.updateLines()
        self.activePlot = 'r'

        #polar plotting
        theta = np.linspace(0, 2*np.pi, 10)
        theta = np.append(theta,0)
        self.theta = theta
        radius = np.zeros(11)
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)

        #polar plots
        polars = [self.grplot_3, self.grplot_4, self.grplot_5]
        for polar in polars:
            polar.setAspectLocked(True)

            # Add polar grid lines
            polar.addLine(x=0, pen=0.2)
            polar.addLine(y=0, pen=0.2)
            for r in range(1, 8, 2):
                circle = pyqtgraph.QtGui.QGraphicsEllipseItem(-r, -r, r*2, r*2)
                circle.setPen(pyqtgraph.mkPen(0.1))
                polar.addItem(circle)
            polar.hideAxis('bottom')
            polar.hideAxis('left')
        
        self.polar1 = polars[0].plot()
        self.polar2 = polars[1].plot()
        self.polar1.setData(x, y)
        self.polar2.setData(x, y)

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
        self.t = Thread(target=self.nexus.run) #Processor)
        self.t.daemon = True
        self.t.start()
        #TODO: grey out button until self.t is done, but allow other buttons to be active

    def update(self):
        ''' Update visualization while running
        '''
        #plot lines
        self.updateLines()

        #plot video
        self.updateVideo()

        #re-update
        if self.checkBox.isChecked():
            QtCore.QTimer.singleShot(100, self.update)
    
    def updateVideo(self):
        image = None
        try:
            raw, image = self.nexus.getPlotRaw()
        except Exception as e:
            logger.error('Oh no {0}'.format(e))
        if image is not None and np.unique(image).size > 1:
            self.rawplot.setImage(raw.T)
            self.rawplot_2.setImage(image.T)
            self.rawplot_3.setImage(image.T)

        # NOTE: not plotting blue circles at the moment.
        # penCont=pyqtgraph.mkPen(width=1, color='b')
        try:
            self.neurCom = self.nexus.getPlotCoM()
        #     if self.neurCom: #add neurons, need to add contours to graph
        #         for c in self.neurCom:
        #             #TODO: delete and re-add circle for all (?) neurons if they've moved beyond a 
        #             # certain distance (set via params...)
        #             self.rawplot_2.getView().addItem(CircleROI(pos = np.array([c[1], c[0]])-5, size=10, movable=False, pen=penCont))
        #     #TODO: keep track of added neurons and likely not update positions, only add new ones.
        except Exception as e:
            logger.error('Something {0}'.format(e))

    def updateLines(self):
        ''' Helper function to plot the line traces
            of the activity of the selected neurons.
            TODO: separate updates for each plot?
        '''
        #plot traces
        pen=pyqtgraph.mkPen(width=2, color='w')
        pen2=pyqtgraph.mkPen(width=2, color='r')
        Y = None
        avg = None
        avgAvg = None
        try:
            #self.ests = self.nexus.getEstimates()
            (X, Y, avg, avgAvg) = self.nexus.getPlotEst()
        except Exception as e:
            logger.info('output does not yet exist. error: {}'.format(e))

        if(Y is not None):
            self.c1.setData(X, Y[1], pen=pen)
            self.c2.setData(X, Y[0], pen=pen2)
            
            if(self.flag):
                self.selected = self.nexus.getFirstSelect()
                print('selected is ', self.selected)
                if self.selected is not None:
                    self._updateRedCirc()
                    #self.flag = False

        if(avg is not None):
            self.radius = np.zeros(11)
            self.radius[:len(avg)] = avg
            self.x = self.radius * np.cos(self.theta)
            self.y = self.radius * np.sin(self.theta)
            self.polar2.setData(self.x, self.y, pen=pyqtgraph.mkPen(width=2, color='r'))

        if(avgAvg is not None):
            self.radius2 = np.zeros(11)
            self.radius2[:len(avgAvg)] = avgAvg
            self.x2 = self.radius2 * np.cos(self.theta)
            self.y2 = self.radius2 * np.sin(self.theta)
            self.polar1.setData(self.x2, self.y2, pen=pyqtgraph.mkPen(width=2, color='w'))

    def mouseClick(self, event):
        '''Clicked on raw image to select neurons
        '''
        #TODO: make this unclickable until finished updated plot (?)
        event.accept()
        mousePoint = event.pos()
        print('Clicked ', mousePoint)
        self.selected = self.nexus.selectNeurons(int(mousePoint.x()), int(mousePoint.y()))
        selectedraw = np.zeros(2)
        selectedraw[0] = int(mousePoint.x())
        selectedraw[1] = int(mousePoint.y())
        #print('selectedRaw is ', selectedraw, ' and found selected is ', self.selected)
        self._updateRedCirc()
            

    def _updateRedCirc(self):
        ''' Circle neuron whose activity is in top (red) graph
            Default is neuron #0 from initialize
            #TODO: raise error if no neurons found (for all plotting..)
            #TODO: add arg instead of self.selected
        '''
        ROIpen1=pyqtgraph.mkPen(width=1, color='r')
        if self.flag:
            self.red_circ = CircleROI(pos = np.array([self.selected[0][1], self.selected[0][0]])-5, size=10, movable=False, pen=ROIpen1)
            self.rawplot_2.getView().addItem(self.red_circ)
            self.flag = False
        if np.count_nonzero(self.selected[0]) > 0:
            self.rawplot_2.getView().removeItem(self.red_circ)
            self.red_circ = CircleROI(pos = np.array([self.selected[0][1], self.selected[0][0]])-5, size=10, movable=False, pen=ROIpen1)
            self.rawplot_2.getView().addItem(self.red_circ)


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

class CircleROI(EllipseROI):
    def __init__(self, pos, size, **args):
        pyqtgraph.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True

class PolyROI(PolyLineROI):
    def __init__(self, positions, pos, **args):
        closed = True
        print('got positions ', positions)
        pyqtgraph.ROI.__init__(self, positions, closed, pos, **args)
        #self.aspectLocked = True

if __name__=="__main__":
    app = QtGui.QApplication(sys.argv)
    rasp = FrontEnd()
    rasp.show()
    app.exec_()
