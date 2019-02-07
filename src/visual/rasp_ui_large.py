# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/visual/rasp_ui_large.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1118, 652)
        MainWindow.setStyleSheet("QMainWindow { background-color: \'blue\'; }")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setStyleSheet("#centralwidget { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 rgb(50, 50, 50), stop:1 rgba(80, 80, 80, 255)); }\n"
"#checkBox {color: black}\n"
"#frame {background-color: rgb(150, 160, 175);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#frame_3 {background-color: rgb(170, 185, 200);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#frame_2 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#frame_4 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#frame_5 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#grplot {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#grplot_2 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#grplot_3 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#grplot_4 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#grplot_5 {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#pushButton {\n"
"background-color: rgb(225, 230, 240);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}\n"
"#pushButton_2 {\n"
"background-color: rgb(225, 230, 240);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}\n"
"#pushButton_3 {\n"
"background-color: rgb(225, 230, 240);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}\n"
"#pushButton_4 {\n"
"background-color: rgb(200, 140, 140);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}")
        self.centralwidget.setObjectName("centralwidget")
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setGeometry(QtCore.QRect(10, 260, 351, 341))
        self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.rawplot = ImageView(self.frame_2)
        self.rawplot.setGeometry(QtCore.QRect(10, 10, 341, 331))
        self.rawplot.setObjectName("rawplot")
        self.frame = QtWidgets.QFrame(self.centralwidget)
        self.frame.setGeometry(QtCore.QRect(10, 10, 151, 241))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.pushButton = QtWidgets.QPushButton(self.frame)
        self.pushButton.setGeometry(QtCore.QRect(20, 10, 111, 51))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(self.frame)
        self.pushButton_2.setGeometry(QtCore.QRect(20, 70, 111, 51))
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_3 = QtWidgets.QPushButton(self.frame)
        self.pushButton_3.setGeometry(QtCore.QRect(20, 130, 111, 51))
        self.pushButton_3.setObjectName("pushButton_3")
        self.checkBox = QtWidgets.QCheckBox(self.frame)
        self.checkBox.setGeometry(QtCore.QRect(20, 190, 111, 41))
        font = QtGui.QFont()
        font.setFamily("Helvetica Neue")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.checkBox.setFont(font)
        self.checkBox.setObjectName("checkBox")
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(200, 140, 401, 95))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.grplot_2 = PlotWidget(self.horizontalLayoutWidget)
        self.grplot_2.setObjectName("grplot_2")
        self.horizontalLayout_3.addWidget(self.grplot_2)
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(620, 20, 111, 101))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.grplot_3 = PlotWidget(self.horizontalLayoutWidget_2)
        self.grplot_3.setObjectName("grplot_3")
        self.horizontalLayout_4.addWidget(self.grplot_3)
        self.horizontalLayoutWidget_3 = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget_3.setGeometry(QtCore.QRect(200, 20, 401, 95))
        self.horizontalLayoutWidget_3.setObjectName("horizontalLayoutWidget_3")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_3)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.grplot = PlotWidget(self.horizontalLayoutWidget_3)
        self.grplot.setObjectName("grplot")
        self.horizontalLayout_5.addWidget(self.grplot)
        self.frame_4 = QtWidgets.QFrame(self.centralwidget)
        self.frame_4.setGeometry(QtCore.QRect(760, 260, 341, 341))
        self.frame_4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_4.setObjectName("frame_4")
        self.rawplot_3 = ImageView(self.frame_4)
        self.rawplot_3.setGeometry(QtCore.QRect(10, 10, 331, 331))
        self.rawplot_3.setObjectName("rawplot_3")
        self.frame_5 = QtWidgets.QFrame(self.centralwidget)
        self.frame_5.setGeometry(QtCore.QRect(390, 260, 341, 341))
        self.frame_5.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_5.setObjectName("frame_5")
        self.rawplot_2 = ImageView(self.frame_5)
        self.rawplot_2.setGeometry(QtCore.QRect(10, 10, 331, 331))
        self.rawplot_2.setObjectName("rawplot_2")
        self.horizontalLayoutWidget_4 = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget_4.setGeometry(QtCore.QRect(620, 140, 111, 101))
        self.horizontalLayoutWidget_4.setObjectName("horizontalLayoutWidget_4")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_4)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.grplot_4 = PlotWidget(self.horizontalLayoutWidget_4)
        self.grplot_4.setObjectName("grplot_4")
        self.horizontalLayout_6.addWidget(self.grplot_4)
        self.frame_3 = QtWidgets.QFrame(self.centralwidget)
        self.frame_3.setGeometry(QtCore.QRect(760, 20, 341, 221))
        self.frame_3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_3.setObjectName("frame_3")
        self.horizontalSlider = QtWidgets.QSlider(self.frame_3)
        self.horizontalSlider.setGeometry(QtCore.QRect(30, 70, 160, 22))
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.horizontalSlider_2 = QtWidgets.QSlider(self.frame_3)
        self.horizontalSlider_2.setGeometry(QtCore.QRect(30, 120, 160, 22))
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.label = QtWidgets.QLabel(self.frame_3)
        self.label.setGeometry(QtCore.QRect(20, 20, 171, 21))
        font = QtGui.QFont()
        font.setFamily("Helvetica Neue")
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.pushButton_4 = QtWidgets.QPushButton(self.frame_3)
        self.pushButton_4.setGeometry(QtCore.QRect(30, 180, 115, 32))
        font = QtGui.QFont()
        font.setFamily("Helvetica Neue")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setObjectName("pushButton_4")
        self.grplot_5 = PlotWidget(self.frame_3)
        self.grplot_5.setGeometry(QtCore.QRect(220, 60, 109, 99))
        self.grplot_5.setObjectName("grplot_5")
        self.frame_2.raise_()
        self.frame.raise_()
        self.horizontalLayoutWidget.raise_()
        self.horizontalLayoutWidget_2.raise_()
        self.horizontalLayoutWidget_3.raise_()
        self.grplot_3.raise_()
        self.frame_4.raise_()
        self.frame_5.raise_()
        self.horizontalLayoutWidget_4.raise_()
        self.grplot_3.raise_()
        self.frame_3.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1118, 22))
        self.menubar.setObjectName("menubar")
        self.menuRASP_Display = QtWidgets.QMenu(self.menubar)
        self.menuRASP_Display.setObjectName("menuRASP_Display")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar.addAction(self.menuRASP_Display.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushButton.setText(_translate("MainWindow", "Load\n"
"Parameters"))
        self.pushButton_2.setText(_translate("MainWindow", "Select\n"
"Processor"))
        self.pushButton_3.setText(_translate("MainWindow", "Run\n"
"Process"))
        self.checkBox.setText(_translate("MainWindow", " Live Update"))
        self.label.setText(_translate("MainWindow", "Targeting Selection"))
        self.pushButton_4.setText(_translate("MainWindow", "Stimulate"))
        self.menuRASP_Display.setTitle(_translate("MainWindow", "Nexus Display"))

from pyqtgraph import ImageView, PlotWidget

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

