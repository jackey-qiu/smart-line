import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from PyQt5 import QtGui
from taurus.qt.qtgui.container import TaurusMainWindow
from smart.gui.main_gui import smartGui

def main():
    import qdarkstyle
    import sardana
    from taurus.core.util import argparse
    from taurus.qt.qtgui.application import TaurusApplication
    sys.path.append(str(Path(__file__).parent.parent))
    sys.path.append(str(Path(__file__).parent.parent / 'gui' / 'widgets'))
    
    parser = argparse.get_taurus_parser()
    parser.set_usage("%prog [options]")
    parser.set_description("Sardana macro sequencer.\n"
                           "It allows the creation of sequences of "
                           "macros, executed one after the other.\n"
                           "The sequences can be stored under xml files")
    parser.add_option("-f", "--file",
                      dest="file", default=None,
                      help="load macro sequence from a file(XML or spock "
                           "syntax)")

    app = TaurusApplication(cmd_line_parser=parser,
                       app_name="sequencer",
                       app_version=sardana.Release.version)
    # app = TaurusApplication(sys.argv)
    # app = TaurusApplication(sys.argv)
    app.setOrganizationName("DESY")
    myWin = smartGui()
    # myWin.init_taurus()
    TaurusMainWindow.loadSettings(myWin)
    myWin.loadSettings()
    myWin.setWindowIcon(QtGui.QIcon(str(Path(__file__).parent / 'desy_small.png')))
    myWin.showMaximized() 
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    myWin.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()