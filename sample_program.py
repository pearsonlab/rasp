from src.nexus.nexus import Nexus
from src.nexus.store import Limbo
from src.nexus.tweak import Tweak
from src.visual.front_end import FrontEnd
from PyQt5 import QtGui
import sys

# Select classes for various Nexus components
nexus = Nexus('my nexus')
tweak = Tweak('stuff') # defines classes here
nexus.loadTweak()
nexus.createNexus()

# Specify location of param file(s)
nexus.setupProcessor()

# Register shared components 


# Register dependencies of ordering between components





if __name__=="__main__":
    app = QtGui.QApplication(sys.argv)
    rasp = FrontEnd()
    rasp.show()
    app.exec_()



