from PyQt5 import QtGui,QtCore,QtWidgets
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from visual import rasp_ui_huge as rasp_ui
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

    # COLOR = {0: ( 26, 239,  27),
    #          1: (230, 230,  94),
    #          2: (239, 131,  27),
    #          3: (239,  26,  80),
    #          4: (193,  31, 194),
    #          5: (119,  96, 169),
    #          6: ( 79,  26, 240),
    #          7: ( 26, 239, 186)}
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
        self.extraSetup()
        pyqtgraph.setConfigOptions(leftButtonPan=False)

        self.customizePlots()

        self.pushButton_3.clicked.connect(_call(self._runProcess)) #Tell Nexus to start
        self.pushButton_3.clicked.connect(_call(self.update)) #Update front-end graphics
        self.pushButton_2.clicked.connect(_call(self._setup))
        self.pushButton.clicked.connect(_call(self._loadParams)) #File Dialog, then tell Nexus to load tweak
        self.checkBox.stateChanged.connect(self.update) #Show live front-end updates
        

        self.rawplot_2.getImageItem().mouseClickEvent = self.mouseClick #Select a neuron
        self.rawplot_3.getImageItem().mouseClickEvent = self.weightClick #select a neuron by weight
        self.slider.valueChanged.connect(_call(self.sliderMoved)) #Threshold for magnitude selection

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
                print('---------------------here' , traceback.format_exc())

            #plot video
            try:
                self.updateVideo()
            except Exception:
                import traceback
                print('---------------------here TWO' , traceback.format_exc())

        #re-update
        if self.checkBox.isChecked():
            self.draw = True
        else:
            self.draw = False    
        self.visual.draw = self.draw
            
        QtCore.QTimer.singleShot(10, self.update)
        
        self.total_times.append([self.visual.frame_num, time.time()-t])

    def extraSetup(self):
        self.slider2 = QRangeSlider(self.frame_3)
        # self.slider2.setGeometry(QtCore.QRect(20, 100, 155, 50))
        self.slider2.setGeometry(QtCore.QRect(55, 120, 155, 50))
        self.slider2.setObjectName("slider2")
        self.slider2.rangeChanged.connect(_call(self.slider2Moved)) #Threshold for angular selection

    def customizePlots(self):
        self.checkBox.setChecked(True)
        self.draw = True

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
        polars = [self.grplot_3, self.grplot_4, self.grplot_5]
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

        for r in range(2, 12, 2):
                circle = pyqtgraph.QtGui.QGraphicsEllipseItem(-r, -r, r*2, r*2)
                circle.setPen(pyqtgraph.mkPen(0.1))
                polars[2].addItem(circle)
        self.polar3 = polars[2].plot()

        #sliders
        self.slider.setMinimum(0)
        self.slider.setMaximum(12)

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
        #self.flag = True
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
        try:
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
                # weight = np.rot90(weight,1)
                self.rawplot_3.setImage(weight)
                colordata = (np.array(cmapToColormap(cm.inferno).color) * 255).astype(np.uint8)
                cmap = ColorMap(pos=np.linspace(0, 1.0, len(colordata)), color=colordata)
                # print('cmap shape', cmap.shape)
                self.rawplot_3.setColorMap(cmap)
                self.rawplot_3.ui.histogram.vb.setLimits(yMin=-1, yMax=1)
            else:
                if image is not None:
                    image = np.rot90(image, 2)
                    self.rawplot_3.setImage(image)
                    self.rawplot_3.ui.histogram.vb.setLimits(yMin=8, yMax=255)

        except Exception as e:
            logger.error('Error in FrontEnd update Video:  {}'.format(e))
            raise Exception

    def updateLines(self):
        ''' Helper function to plot the line traces
            of the activity of the selected neurons.
            TODO: separate updates for each plot?
        '''
        penW=pyqtgraph.mkPen(width=2, color='w')
        penR=pyqtgraph.mkPen(width=2, color='r')
        C = None
        Cx = None
        tune = None
        try:
            (Cx, C, Cpop, tune) = self.visual.getCurves()
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
                    # print(display)
                    plot.setData(display, [10] * len(display),
                                 symbol='s', symbolSize=6, antialias=False,
                                 pen=None, symbolPen=self.COLOR[i], symbolBrush=self.COLOR[i])
            self.c2.setData(Cx, C, pen=penR)
            
            if(self.flag):
                self.selected = self.visual.getFirstSelect()
                if self.selected is not None:
                    self._updateRedCirc()

        #TODO: rewrite as set of polar[] and set of tune[]
        if tune is not None:
            self.num = tune[0].shape[0]
            theta = np.linspace(0, (315/360)*2*np.pi, self.num)
            theta = np.append(theta,0)
            self.theta = theta  
            if(tune[0] is not None):
                self.radius = np.zeros(self.num+1)
                self.radius[:len(tune[0])] = tune[0]/np.max(tune[0])
                self.radius[-1] = self.radius[0]
                #self.radius = np.roll(self.radius,2)
                self.x = np.clip(self.radius * np.cos(self.theta) * 4, -5, 5)
                self.y = np.clip(self.radius * np.sin(self.theta) * 4, -5, 5)
                self.polar2.setData(self.x, self.y, pen=penR)

            if(tune[1] is not None):
                self.radius2 = np.zeros(self.num+1)
                self.radius2[:len(tune[1])] = tune[1]/np.max(tune[1])
                self.radius2[-1] = self.radius2[0]
                #self.radius2 = np.roll(self.radius2,2)
                self.x2 = np.clip(self.radius2 * np.cos(self.theta) * 4, -5, 5)
                self.y2 = np.clip(self.radius2 * np.sin(self.theta) * 4, -5, 5)
                self.polar1.setData(self.x2, self.y2, pen=penW)
        # else:
        #     logger.error('Visual received None tune')
        
    def mouseClick(self, event):
        '''Clicked on raw image to select neurons
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
            self.lines = []
            self.pens = []
            for i in range(9):
                n = lines[i]
                if strengths[i] > 1e-5:
                    if strengths[i] > 1e-4:
                        self.pens.append(pyqtgraph.mkPen(width=2, color='g'))
                    else:
                        self.pens.append(pyqtgraph.mkPen(width=1, color='g'))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])
                else:
                    self.pens.append(pyqtgraph.mkPen(width=1, color='g'))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[0]],[n[0],n[0]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])

            self.last_n = self.visual.selectedNeuron
            self.flagW = False
        elif self.last_n == self.visual.selectedNeuron:
            for i in range(9):
                self.rawplot_2.getView().removeItem(self.lines[i])
            self.flagW = True


    def weightClick(self, event):
        '''Clicked on weight image to select neurons
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
            for i in range(9):
                n = lines[i]
                if strengths[i] > 1e-5:
                    if strengths[i] > 1e-4:
                        self.pens.append(pyqtgraph.mkPen(width=2, color='g'))
                    else:
                        self.pens.append(pyqtgraph.mkPen(width=1, color='g'))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])
                else:
                    self.pens.append(pyqtgraph.mkPen(width=1, color='g'))
                    self.lines.append(LineSegmentROI(positions=([n[0],n[0]],[n[0],n[0]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])

            self.last_x = int(mousePoint.x())
            self.last_y = int(mousePoint.y())

            self.flagW = False
        else:
            self.rawplot_3.getView().removeItem(self.rect)
            self.rawplot_3.getView().removeItem(self.rect2)

            self.rawplot_2.getView().removeItem(self.green_circ)
            for i in range(9):
                self.rawplot_2.getView().removeItem(self.lines[i])

            print('confirmed removed')

            if self.last_x != int(mousePoint.x()) or self.last_y != int(mousePoint.y()):
                self.rect = ROI(pos = (int(mousePoint.x()), 0), size=(1,10), pen=pen, movable=False)
                self.rect2 = ROI(pos = (0, int(mousePoint.y())), size=(10,1), pen=pen2, movable=False)
                self.rawplot_3.getView().addItem(self.rect)
                self.rawplot_3.getView().addItem(self.rect2)

                pen = pyqtgraph.mkPen(width=1, color='g')
                self.green_circ = CircleROI(pos = np.array([loc[0][0], loc[0][1]])-5, size=10, movable=False, pen=pen)
                self.rawplot_2.getView().addItem(self.green_circ)

                for i in range(9):
                    n = lines[i]
                    if strengths[i] > 1e-5:
                        if strengths[i] > 1e-4:
                            self.pens[i] = (pyqtgraph.mkPen(width=2, color='g'))
                        else:
                            self.pens[i] = (pyqtgraph.mkPen(width=1, color='g'))
                        self.lines[i] = (LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
                    else:
                        self.pens[i] = (pyqtgraph.mkPen(width=1, color='g'))
                        self.lines[i] = (LineSegmentROI(positions=([n[0],n[0]],[n[0],n[0]]), handles=(None,None), pen=self.pens[i], movable=False))
                    self.rawplot_2.getView().addItem(self.lines[i])
                self.last_x = int(mousePoint.x())
                self.last_y = int(mousePoint.y())
            else:
                self.flagW = True

        # if self.flagL:
        #     pen = pyqtgraph.mkPen(width=1, color='g')
        #     self.green_circ = CircleROI(pos = np.array([loc[0][0], loc[0][1]])-5, size=10, movable=False, pen=pen)
        #     self.rawplot_2.getView().addItem(self.green_circ)
        #     self.lines = []
        #     self.pens = []
        #     for i in range(9):
        #         n = lines[i]
        #         self.pens.append(pyqtgraph.mkPen(width=2, color='g'))
        #         self.lines.append(LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
        #         self.rawplot_2.getView().addItem(self.lines[i])
        #     self.flagL = False
        # else:
        #     self.rawplot_3.getView().removeItem(self.green_circ)
        #     pen = pyqtgraph.mkPen(width=1, color='g')
        #     self.green_circ = CircleROI(pos = np.array([loc[0][0], loc[0][1]])-5, size=10, movable=False, pen=pen)
        #     self.rawplot_2.getView().addItem(self.green_circ)
        #     for i in range(9):
        #         n = lines[i]
        #         self.rawplot_2.getView().removeItem(self.lines[i])
        #         self.lines[i] = (LineSegmentROI(positions=([n[0],n[2]],[n[1],n[3]]), handles=(None,None), pen=self.pens[i], movable=False))
        #         self.rawplot_2.getView().addItem(self.lines[i])
                    
    # def _updateRect(self):
    #     # follow selected neuron with rectangles (unless it disappears?)
    #     if self.weightN is not None:


    def sliderMoved(self):
        val = self.slider.value()
        if np.count_nonzero(self.thresh_r) == 0:
            r = np.full(self.num+1,val)
        else:
            r = self.thresh_r
            r[np.nonzero(r)] = val
        self.updateThreshGraph(r)

    def slider2Moved(self):
        r1,r2 = self.slider2.range()
        r = np.full(self.num+1, self.slider.value())
        r1 = 4*np.pi*(r1-4)/360
        r2 = 4*np.pi*(r2-4)/360
        t1 = np.argmin(np.abs(np.array(r1)-self.theta))
        t2 = np.argmin(np.abs(np.array(r2)-self.theta))
        r[0:t1] = 0
        r[t2+1:self.num] = 0
        r[-1] = r[0]
        self.updateThreshGraph(r)

    def updateThreshGraph(self, r):
        self.thresh_r = r
        x = self.thresh_r * np.cos(self.theta)
        y = self.thresh_r * np.sin(self.theta)
        self.polar3.setData(x, y, pen=pyqtgraph.mkPen(width=2, color='g'))

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

class QRangeSlider(QtWidgets.QWidget):

    rangeChanged = pyqtSignal(tuple, name='rangeChanged')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._minimum = 0
        self._maximum = 180

        self.min_max = 99
        self.max_max = 99

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(0)
        self.setLayout(self._layout)

        self._min_slider = QtWidgets.QSlider(Qt.Horizontal)
        self._min_slider.setInvertedAppearance(True)

        self._max_slider = QtWidgets.QSlider(Qt.Horizontal)

        # install update handlers
        for slider in [self._min_slider, self._max_slider]:
            slider.blockSignals(True)
            slider.valueChanged.connect(self._value_changed)
            slider.rangeChanged.connect(self._update_layout)

            self._layout.addWidget(slider)
 
        # initialize to reasonable defaults
        self._min_slider.setValue(1 * self._min_slider.maximum())
        self._max_slider.setValue(1 * self._max_slider.maximum())

        self._update_layout()

    def _value_changed(self, *args):
        self._update_layout()
        self.rangeChanged.emit(self.range())

    def _update_layout(self, *args):
        for slider in [self._min_slider, self._max_slider]:
            slider.blockSignals(True)

        mid = floor((self._max_slider.value()-self._min_slider.value())/ 2)

        self.setMax_min(self._min_slider.maximum() + mid)
        self._min_slider.setValue(self._min_slider.value() + mid)
        self.setMax_max(self._max_slider.maximum() - mid)
        self._max_slider.setValue(self._max_slider.value() - mid)

        for slider in [self._min_slider, self._max_slider]:
            slider.blockSignals(False)

        self._layout.setStretch(0, self._min_slider.maximum())
        self._layout.setStretch(1, self._max_slider.maximum())

    def setMax_min(self, value):
        self._min_slider.setMaximum(value)
        self.min_max = value

    def setMax_max(self, value):
        self._max_slider.setMaximum(value)
        self.max_max = value

    def getMax_min(self):
        return self.min_max

    def getMax_max(self):
        return self.max_max

    def lowerSlider(self):
        return self._min_slider

    def upperSlider(self):
        return self._max_slider

    def range(self):
        return (self.getMax_min() - self._min_slider.value(), 180 - (self.getMax_max() - self._max_slider.value()))

    def setRange(self, lower, upper):
        for slider in [self._min_slider, self._max_slider]:
            slider.blockSignals(True)
        self._update_layout()


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
