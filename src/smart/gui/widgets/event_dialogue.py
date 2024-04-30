from PyQt5.QtWidgets import QMessageBox

def error_pop_up(msg_text = 'error', window_title = ['Error','Information','Warning'][0]):
    msg = QMessageBox()
    if window_title == 'Error':
        msg.setIcon(QMessageBox.Critical)
    elif window_title == 'Warning':
        msg.setIcon(QMessageBox.Warning)
    else:
        msg.setIcon(QMessageBox.Information)

    msg.setText(msg_text)
    msg.setWindowTitle(window_title)
    msg.exec_()

def confirmation_dialogue(msg, parent = None):
    reply = QMessageBox.question(parent, 'Message', \
                    msg, QMessageBox.Yes, QMessageBox.No)
    if reply == QMessageBox.Yes:        
        return True
    elif reply == QMessageBox.No:
        return False