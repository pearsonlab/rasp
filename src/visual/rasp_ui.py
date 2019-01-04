# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './src/visual/rasp_ui.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        MainWindow.setStyleSheet("QMainWindow { background-color: \'blue\'; }")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setStyleSheet("#centralwidget { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 rgb(164, 186, 224), stop:1 rgba(180, 200, 255, 255)); }\n"
"#frame {border-style: outset;\n"
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
"#grplot {background: rgb(229, 229, 229);\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px}\n"
"#pushButton {\n"
"background-color: rgb(229, 229, 229);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}\n"
"#pushButton_2 {\n"
"background-color: rgb(229, 229, 229);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}\n"
"#pushButton_3 {\n"
"background-color: rgb(229, 229, 229);\n"
"color: black;\n"
"font: bold;\n"
"border-style: outset;\n"
"border-width: 2px;\n"
"border-radius: 10px;\n"
"border-color: black;\n"
"padding: 6px\n"
"}")
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalWidget1 = QtWidgets.QWidget(self.centralwidget)
        self.horizontalWidget1.setGeometry(QtCore.QRect(10, 10, 301, 261))
        self.horizontalWidget1.setObjectName("horizontalWidget1")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalWidget1)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtWidgets.QFrame(self.horizontalWidget1)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.pushButton = QtWidgets.QPushButton(self.frame)
        self.pushButton.setGeometry(QtCore.QRect(140, 40, 115, 81))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(self.frame)
        self.pushButton_2.setGeometry(QtCore.QRect(20, 40, 115, 81))
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_3 = QtWidgets.QPushButton(self.frame)
        self.pushButton_3.setGeometry(QtCore.QRect(20, 130, 115, 81))
        self.pushButton_3.setObjectName("pushButton_3")
        self.label = QtWidgets.QLabel(self.frame)
        self.label.setGeometry(QtCore.QRect(40, 10, 211, 20))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.checkBox = QtWidgets.QCheckBox(self.frame)
        self.checkBox.setGeometry(QtCore.QRect(150, 150, 101, 41))
        font = QtGui.QFont()
        font.setFamily("Helvetica Neue")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.checkBox.setFont(font)
        self.checkBox.setObjectName("checkBox")
        self.horizontalLayout.addWidget(self.frame)
        self.verticalWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalWidget.setGeometry(QtCore.QRect(9, 319, 771, 211))
        self.verticalWidget.setObjectName("verticalWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.grplot = PlotWidget(self.verticalWidget)
        self.grplot.setObjectName("grplot")
        self.verticalLayout.addWidget(self.grplot)
        self.horizontalWidget2 = QtWidgets.QWidget(self.centralwidget)
        self.horizontalWidget2.setGeometry(QtCore.QRect(340, 10, 431, 301))
        self.horizontalWidget2.setObjectName("horizontalWidget2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalWidget2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.frame_2 = QtWidgets.QFrame(self.horizontalWidget2)
        self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.rawplot = ImageView(self.frame_2)
        self.rawplot.setGeometry(QtCore.QRect(10, 10, 411, 291))
        self.rawplot.setObjectName("rawplot")
        self.horizontalLayout_2.addWidget(self.frame_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
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
        self.label.setText(_translate("MainWindow", "Configuration & Control"))
        self.checkBox.setText(_translate("MainWindow", "Continuous\n"
"Update"))
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

