import sys
import os
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    # Ensure we are in the right directory to find src
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    sys.path.append(script_dir)

    app = QApplication(sys.argv)
    app.setApplicationName("XTREME IPTV PLAYER PRO")
    
    # Limit global thread pool to avoid resource exhaustion
    from PyQt5.QtCore import QThreadPool
    QThreadPool.globalInstance().setMaxThreadCount(4)
    
    # Load stylesheet
    qss_path = os.path.join(script_dir, "src", "assets", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
