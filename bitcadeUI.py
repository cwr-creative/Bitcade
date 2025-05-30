import os
import sys
import multiprocessing
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtProperty, QTimer
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap

# Set before QApplication for transparency and performance on X11
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_X11_NO_MITSHM"] = "1"

class OverlayWindow(QWidget):
    def __init__(self, command_queue):
        super().__init__()
        self.command_queue = command_queue
        self._opacity = 0.0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(400, 150)
        self.move(QApplication.primaryScreen().geometry().width() - 420,
                  QApplication.primaryScreen().geometry().height() - 200)

        # Load custom font
        font_path = "$HOME/bitcade/Bitcade/fonts/Symtext.ttf"
        QFontDatabase.addApplicationFont(font_path)

        # Credit label
        self.label = QLabel("Credits: 0", self)
        self.label.setStyleSheet("color: white; font-size: 30px;")
        self.label.setFont(QFont("Symtext", 32))
        self.label.move(20, 20)

        # Sprite overlay (for animation)
        self.sprite = QLabel(self)
        self.sprite.setVisible(False)

        # Fade animation
        self.anim = QPropertyAnimation(self, b"opacity")
        self.anim.setDuration(500)

        # Timer to hide the overlay
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def set_opacity(self, val):
        self._opacity = val
        self.setWindowOpacity(val)

    def get_opacity(self):
        return self._opacity

    opacity = pyqtProperty(float, fget=get_opacity, fset=set_opacity)

    def fade_in(self):
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def show_credits(self, previous, current):
        self.label.setText(f"Credits: {previous}")
        self.fade_in()
        self.sprite.setVisible(False)
        self.show()

        # Begin PNG overlay animation after fade-in
        QTimer.singleShot(500, lambda: self.play_sprite(previous, current))

    def play_sprite(self, previous, current):
        sprite_path = os.path.expanduser("~/bitcade/Bitcade/sprites/fire-%02d.png")
        frames = [QPixmap(sprite_path % i) for i in range(1, 5)]

        from PyQt5.QtGui import QFontMetrics

# Get width of "Credits: " in pixels
        prefix = "Credits: "
        metrics = QFontMetrics(self.label.font())

        # Set position: align sprite with the number (right of the prefix)
        label_geom = self.label.geometry()
        sprite_x = label_geom.x() + 158
        sprite_y = label_geom.y() + 4

        # Set sprite size to match PNG frame (or adjust as needed)
        frame = frames[0]
        self.sprite.setPixmap(frame)
        self.sprite.setGeometry(sprite_x, sprite_y, frame.width(), frame.height())

        self.sprite.setVisible(True)
        self.sprite.setStyleSheet("background: transparent;")
        self.sprite.raise_()

        def update_frame(i=0):
            if i == 2:
                self.label.setText(f"Credits: {current}")
            if i >= len(frames):
                self.sprite.setVisible(False)
                self.hide_timer.start(500)
                return
            self.sprite.setPixmap(frames[i])
            QTimer.singleShot(100, lambda: update_frame(i + 1))

        update_frame()

def run_overlay(command_queue):
    app = QApplication(sys.argv)
    window = OverlayWindow(command_queue)

    def check_queue():
        while not command_queue.empty():
            cmd, args = command_queue.get_nowait()
            if cmd == "show_credits":
                prev, curr = args
                window.show_credits(prev, curr)

    # Poll the queue
    timer = QTimer()
    timer.timeout.connect(check_queue)
    timer.start(100)

    window.show()
    sys.exit(app.exec_())

# Optional test mode
if __name__ == "__main__":
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=run_overlay, args=(queue,))
    p.start()

    import time
    time.sleep(3)
    queue.put(("show_credits", (3, 2)))
    time.sleep(10)
    p.terminate()
