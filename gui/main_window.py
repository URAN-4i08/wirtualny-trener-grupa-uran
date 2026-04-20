from PyQt6.QtWidgets import QMainWindow, QLabel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wirtualny Trener - CyberTrener")
        self.resize(800, 600)
        
        label = QLabel("Witaj w aplikacji Wirtualny Trener!", self)
        self.setCentralWidget(label)
