import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from PyQt5 import QtGui
from taurus.qt.qtgui.container import TaurusMainWindow
from smart.gui.main_gui import smartGui
import click

@click.command()
@click.option('--config', default='default',
              help="specify the path of configuration file. If use default, the default config file will be used")
def main(config):
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
    parser.add_option("-c", "--config",
                      dest="config file", default=None,
                      help="load user specified config file ")
                           
    app = TaurusApplication(cmd_line_parser=parser,
                       app_name="SMART",
                       app_version=sardana.Release.version)
    
    '''
    app = TaurusApplication(
                       app_name="SMART",
                       app_version='1.0.0')
    
    '''
    # app = TaurusApplication(sys.argv)
    # app = TaurusApplication(sys.argv)
    app.setOrganizationName("DESY")
    if config=='default':
        myWin = smartGui()
    else:
        import os
        if os.path.isfile(config):
            print(config)
            myWin = smartGui(config=config)
        else:
            print('The provided config file is not existing! Use default config instead!')
            myWin = smartGui()
    # myWin.init_taurus()
    TaurusMainWindow.loadSettings(myWin)
    myWin.loadSettings()
    myWin.setWindowIcon(QtGui.QIcon(str(Path(__file__).parent / 'smart_logo.png')))
    myWin.setWindowTitle("SMART")
    myWin.showMaximized() 
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    myWin.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()