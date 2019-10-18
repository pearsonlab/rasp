from PyQt5 import QtGui,QtCore,QtWidgets
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from visual import improv_fit as rasp_ui
from nexus.store import Limbo
from nexus.actor import Spike
import numpy as np
from math import floor
import time
import pyqtgraph
from pyqtgraph import EllipseROI, PolyLineROI, ColorMap, ROI, LineSegmentROI
from queue import Empty
from matplotlib import cm
from matplotlib.colors import ListedColormap

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#NOTE: GUI only gives comm signals to Nexus, does not receive any. Visual serves that role
#TODO: Add ability to receive signals like pause updating ...?

class FrontEnd(QtGui.QMainWindow, rasp_ui.Ui_MainWindow):

    COLOR = {0: ( 240, 122,  5),
             1: (181, 240,  5),
             2: (5, 240,  5),
             3: (5,  240,  181),
             4: (5,  122, 240),
             5: (64,  5, 240),
             6: ( 240,  5, 240),
             7: ( 240, 5, 64)}

    def __init__(self, visual, comm, parent=None):
        ''' Setup GUI
            Setup and start Nexus controls
        '''
        self.visual = visual #Visual class that provides plots and images
        self.comm = comm #Link back to Nexus for transmitting signals

        self.total_times = []

        pyqtgraph.setConfigOption('background', QColor(100, 100, 100))
        super(FrontEnd, self).__init__(parent)
        self.setupUi(self)
        pyqtgraph.setConfigOptions(leftButtonPan=False)

        self.customizePlots()

        self.pushButton_3.clicked.connect(_call(self._runProcess)) #Tell Nexus to start
        self.pushButton_3.clicked.connect(_call(self.update)) #Update front-end graphics
        self.pushButton_2.clicked.connect(_call(self._setup))
        self.pushButton.clicked.connect(_call(self._loadParams)) #File Dialog, then tell Nexus to load tweak
        self.checkBox.stateChanged.connect(self.update) #Show live front-end updates
        
        self.rawplot_2.getImageItem().mouseClickEvent = self.mouseClick #Select a neuron
        self.rawplot_3.getImageItem().mouseClickEvent = self.weightClick #select a neuron by weight

    def update(self):
        ''' Update visualization while running
        '''
        t = time.time()
        #start looking for data to display
        self.visual.getData()
        #logger.info('Did I get something:', self.visual.Cx)

        if self.draw:
            #plot lines
            try:
                self.updateLines()
            except Exception:
                import traceback
                print('---------------------Exception in update lines: ' , traceback.format_exc())

            #plot video
            try:
                self.updateVideo()
            except Exception:
                logger.error('Error in FrontEnd update Video:  {}'.format(e))
                import traceback
                print('---------------------Exception in update video: ' , traceback.format_exc())

        #re-update
        if self.checkBox.isChecked():
            self.draw = True
        else:
            self.draw = False    
        self.visual.draw = self.draw
            
        QtCore.QTimer.singleShot(10, self.update)
        
        self.total_times.append([self.visual.frame_num, time.time()-t])

    def customizePlots(self):
        self.checkBox.setChecked(True)
        self.draw = True

        pixmap = QPixmap('src/visual/rainbow_dir.png')
        pixmap = pixmap.scaled(60, 60) #, QtCore.Qt.KeepAspectRatio)
        self.dir_icon.setPixmap(pixmap)

        #init line plot
        self.flag = True
        self.flagW = True
        self.flagL = True
        self.last_x = None
        self.last_y = None
        self.weightN = None
        self.last_n = None

        self.c1 = self.grplot.plot(clipToView=True)
        self.c1_stim = [self.grplot.plot(clipToView=True) for _ in range(len(self.COLOR))]
        self.c2 = self.grplot_2.plot()
        self.llPlot = self.grplot_5.plot()
        grplot = [self.grplot, self.grplot_2]
        for plt in grplot:
            plt.getAxis('bottom').setTickSpacing(major=50, minor=50)
        #    plt.setLabel('bottom', "Frames")
        #    plt.setLabel('left', "Temporal traces")
        self.updateLines()
        self.activePlot = 'r'

        #polar plotting
        self.num = 8
        theta = np.linspace(0, (315/360)*2*np.pi, self.num)
        theta = np.append(theta,0)
        self.theta = theta
        radius = np.zeros(self.num+1)
        self.thresh_r = radius + 1
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)

        #polar plots
        polars = [self.grplot_3, self.grplot_4]
        for polar in polars:
            polar.setAspectLocked(True)

            # Add polar grid lines
            polar.addLine(x=0, pen=0.2)
            polar.addLine(y=0, pen=0.2)
            for r in range(0, 4, 1):
                circle = pyqtgraph.QtGui.QGraphicsEllipseItem(-r, -r, r*2, r*2)
                circle.setPen(pyqtgraph.mkPen(0.1))
                polar.addItem(circle)
            polar.hideAxis('bottom')
            polar.hideAxis('left')
        
        self.polar1 = polars[0].plot()
        self.polar2 = polars[1].plot()
        self.polar1.setData(x, y)
        self.polar2.setData(x, y)

        #videos
        #self.rawplot.ui.histogram.vb.disableAutoRange()
        self.rawplot.ui.histogram.vb.setLimits(yMin=-0.1, yMax=200) #0-255 needed, saturated here for easy viewing

        # if self.visual.showConnectivity:
        #     self.rawplot_3.setColorMap(cmapToColormap(cm.inferno))

    def _loadParams(self):
        ''' Button event to load parameters from file
            File location determined from user input
            Throws FileNotFound error
        '''
        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')
            #TODO: make default home folder system-independent
        try:
            self._loadTweak(fname[0])
        except FileNotFoundError as e:
            logger.error('File not found {}'.format(e))
            #raise FileNotFoundError
    
    def _runProcess(self):
        '''Run ImageProcessor in separate thread
        '''
        self.comm.put([Spike.run()])
        logger.info('-------------------------   put run in comm')
        #TODO: grey out button until self.t is done, but allow other buttons to be active

    def _setup(self):
        self.comm.put([Spike.setup()])
        self.visual.setup()

    def _loadTweak(self, file):
        self.comm.put(['load', file])
    
    def updateVideo(self):
        ''' TODO: Bug on clicking ROI --> trace and report to pyqtgraph
        '''
        image = None
        raw, color, weight = self.visual.getFrames()
        image = self.visual.plotThreshFrame(self.thresh_r*2)
        if raw is not None:
            raw = np.rot90(raw,2)
            if np.unique(raw).size > 1:
                self.rawplot.setImage(raw, autoHistogramRange=False)
                self.rawplot.ui.histogram.vb.setLimits(yMin=50)
        if color is not None:
            color = np.rot90(color,2)
            self.rawplot_2.setImage(color)
            self.rawplot_2.ui.histogram.vb.setLimits(yMin=8, yMax=255)

        if self.visual.showConnectivity and weight is not None:
            self.rawplot_3.setImage(weight)
            colordata = (np.array(cmapToColormap(cm.inferno).color) * 255).astype(np.uint8)
            cmap = ColorMap(pos=np.linspace(0, 1.0, len(colordata)), color=colordata)
            self.rawplot_3.setColorMap(cmap)
            self.rawplot_3.ui.histogram.vb.setLimits(yMin=-1, yMax=1)
        else:
            if image is not None:
                image = np.rot90(image, 2)
                self.rawplot_3.setImage(image)
                self.rawplot_3.ui.histogram.vb.setLimits(yMin=8, yMax=255)

    def updateLines(self):
        ''' Helper function to plot the line traces
            of the activity of the selected neurons.
            TODO: separate updates for each plot?
        '''
        penW=pyqtgraph.mkPen(width=2, color='w')
        penR=pyqtgraph.mkPen(width=2, color='r')
        penG=pyqtgraph.mkPen(width=3, color='g')
        C = None
        Cx = None
        tune = None
        LL = None
        try:
            (Cx, C, Cpop, tune, LL) = self.visual.getCurves()
        except TypeError:
            pass
        except Exception as e:
            logger.error('Output does not likely exist. Error: {}'.format(e))

        if(C is not None and Cx is not None):
            self.c1.setData(Cx, Cpop, pen=penW)

            for i, plot in enumerate(self.c1_stim):
                if len(self.visual.stimStatus[i]) > 0:
                    display = np.array(self.visual.stimStatus[i])
                    display = display[display>np.min(Cx)]
                    plot.setData(display, [int(np.max(Cpop))+1] * len(display),
                                 symbol='s', symbolSize=6, antialias=False,
                                 pen=None, symbolPen=self.COLOR[i], symbolBrush=self.COLOR[i])

            self.c2.setData(Cx, C, pen=penR)
            
            if(self.flag):
                self.selected = self.visual.getFirstSelect()
                if self.selected is not None:
                    self._updateRedCirc()

        if(LL is not None and Cx is not None):
            self.llPlot.setData(np.arange(0, len(LL)), LL, pen=penG)

        if tune is not None:
            self.num = tune[0].shape[0]
            theta = np.linspace(0, (315/360)*2*np.pi, self.num)
            theta = np.append(theta,0)
            self.theta = theta  
            polar = [self.polar1, self.polar2]
            pens = [penW, penR]
            for i,t in enumerate(tune):
                if(t is not None):
                    radius = np.zeros(self.num+1)
                    radius[:len(t)] = t/np.max(t)
                    radius[-1] = radius[0]
                    x = np.clip(radius * np.cos(self.theta) * 4, -5, 5)
                    y = np.clip(radius * np.sin(self.theta) * 4, -5, 5)
                    polar[i].setData(x, y, pen=pens[i])
        
    def mouseClick(self, event):
        '''Clicked on processed image to select neurons
        '''
        #TODO: make this unclickable until finished updated plot (?)
        event.accept()
        mousePoint = event.pos()
        self.selected = self.visual.selectNeurons(int(mousePoint.x()), int(mousePoint.y()))
        selectedraw = np.zeros(2)
        selectedraw[0] = int(mousePoint.x())
        selectedraw[1] = int(mousePoint.y())
        self._updateRedCirc()

        if self.last_n is None:
            self.last_n = self.visual.selectedNeuron

        if self.flagW: #nothing drawn yet
            loc, lines, strengths = self.visual.selectNW(selectedraw[0], selectedraw[1])
            # print('clicked lines ', lines)
            self.lines = []
            self.pens = []
            colors =['g']*9 + ['r']*9
            for i in range(18):
                n = lines[i]
                if strengths[i] > 1e-6:
                    if strengths[i] > 1e-4:
                        self.pens.append(pyqtgraph.mkPen(width=2, color=colors[i]))
                    else:
                        self.pens.append(pyqtgraph.mkPen(width=1, color=colors[i]))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])
                else:
                    self.pens.append(pyqtgraph.mkPen(width=1, color=colors[i]))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[0]],[n[0],n[0]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])

            self.last_n = self.visual.selectedNeuron
            self.flagW = False
        elif self.last_n == self.visual.selectedNeuron:
            for i in range(18):
                self.rawplot_2.getView().removeItem(self.lines[i])
            self.flagW = True


    def weightClick(self, event):
        '''Clicked on weight matrix to select neurons
        '''
        event.accept()
        mousePoint = event.pos()
        print('mousepoint: ', int(mousePoint.x()), int(mousePoint.y()))
        if self.last_x is None:
            self.last_x = int(mousePoint.x())
            self.last_y = int(mousePoint.y())
        pen=pyqtgraph.mkPen(width=2, color='r')
        pen2=pyqtgraph.mkPen(width=2, color='r')

        loc, lines, strengths = self.visual.selectWeights(int(mousePoint.x()), int(mousePoint.y()))

        if self.flagW: # need to draw, currently off
            self.rect = ROI(pos = (int(mousePoint.x()), 0), size=(1,10), pen=pen, movable=False)
            self.rect2 = ROI(pos = (0, int(mousePoint.y())), size=(10,1), pen=pen2, movable=False)
            self.rawplot_3.getView().addItem(self.rect)
            self.rawplot_3.getView().addItem(self.rect2)

            pen = pyqtgraph.mkPen(width=1, color='g')
            self.green_circ = CircleROI(pos = np.array([loc[0][0], loc[0][1]])-5, size=10, movable=False, pen=pen)
            self.rawplot_2.getView().addItem(self.green_circ)
            self.lines = []
            self.pens = []
            colors =['g']*9 + ['r']*9
            for i in range(18):
                n = lines[i]
                if strengths[i] > 1e-6:
                    if strengths[i] > 1e-4:
                        self.pens.append(pyqtgraph.mkPen(width=2, color=colors[i]))
                    else:
                        self.pens.append(pyqtgraph.mkPen(width=1, color=colors[i]))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])
                else:
                    self.pens.append(pyqtgraph.mkPen(width=1, color=colors[i]))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[0]],[n[0],n[0]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])

            self.last_x = int(mousePoint.x())
            self.last_y = int(mousePoint.y())

            self.flagW = False
        else:
            self.rawplot_3.getView().removeItem(self.rect)
            self.rawplot_3.getView().removeItem(self.rect2)

            self.rawplot_2.getView().removeItem(self.green_circ)
            for i in range(18):
                self.rawplot_2.getView().removeItem(self.lines[i])

            if self.last_x != int(mousePoint.x()) or self.last_y != int(mousePoint.y()):
                self.rect = ROI(pos = (int(mousePoint.x()), 0), size=(1,10), pen=pen, movable=False)
                self.rect2 = ROI(pos = (0, int(mousePoint.y())), size=(10,1), pen=pen2, movable=False)
                self.rawplot_3.getView().addItem(self.rect)
                self.rawplot_3.getView().addItem(self.rect2)

                pen = pyqtgraph.mkPen(width=1, color='g')
                self.green_circ = CircleROI(pos = np.array([loc[0][0], loc[0][1]])-5, size=10, movable=False, pen=pen)
                self.rawplot_2.getView().addItem(self.green_circ)

                colors =['g']*9 + ['r']*9
                for i in range(18):
                    n = lines[i]
                    if strengths[i] > 1e-6:
                        if strengths[i] > 1e-4:
                            self.pens[i] = (pyqtgraph.mkPen(width=2, color=colors[i]))
                        else:
                            self.pens[i] = (pyqtgraph.mkPen(width=1, color=colors[i]))
                        self.lines[i] = (LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
                    else:
                        self.pens[i] = (pyqtgraph.mkPen(width=1, color=colors[i]))
                        self.lines[i] = (LineSegmentROI(positions=([n[0],n[0]],[n[0],n[0]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])
                self.last_x = int(mousePoint.x())
                self.last_y = int(mousePoint.y())
            else:
                self.flagW = True

    def _updateRedCirc(self):
        ''' Circle neuron whose activity is in top (red) graph
            Default is neuron #0 from initialize
            #TODO: add arg instead of self.selected
        '''
        ROIpen1=pyqtgraph.mkPen(width=1, color='r')
        if self.flag:
            self.red_circ = CircleROI(pos = np.array([self.selected[0][0], self.selected[0][1]])-5, size=10, movable=False, pen=ROIpen1)
            self.rawplot_2.getView().addItem(self.red_circ)
            self.flag = False
        if np.count_nonzero(self.selected[0]) > 0:
            self.rawplot_2.getView().removeItem(self.red_circ)
            self.red_circ = CircleROI(pos = np.array([self.selected[0][0], self.selected[0][1]])-5, size=10, movable=False, pen=ROIpen1)
            self.rawplot_2.getView().addItem(self.red_circ)

    def closeEvent(self, event):
        '''Clicked x/close on window
            Add confirmation for closing without saving
        '''
        confirm = QMessageBox.question(self, 'Message', 'Quit without saving?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.comm.put(['quit'])
            # print('Visual broke, avg time per frame: ', np.mean(self.visual.total_times, axis=0))
            print('Visual got through ', self.visual.frame_num, ' frames')
            # print('GUI avg time ', np.mean(self.total_times))
            np.savetxt('timing/visual_frame_time.txt', np.array(self.visual.total_times))
            np.savetxt('timing/gui_frame_time.txt', np.array(self.total_times))
            np.savetxt('timing/visual_timestamp.txt', np.array(self.visual.timestamp))
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

def cmapToColormap(cmap: ListedColormap) -> ColorMap:
    """ Converts matplotlib cmap to pyqtgraph ColorMap. """

    colordata = (np.array(cmap.colors) * 255).astype(np.uint8)
    indices = np.linspace(0., 1., len(colordata))
    return ColorMap(indices, colordata)


if __name__=="__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    rasp = FrontEnd(None,None)
    rasp.show()
    app.exec_()
