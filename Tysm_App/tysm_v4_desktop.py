"""Windows transparent V4 desktop overlay. Requires PySide6 and PySide6-Addons (QtWebEngine)."""
import sys
import json
from urllib.request import urlopen
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

class Overlay(QWebEngineView):
    def __init__(self, url, rect, boot=False):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.setGeometry(*rect)
        self.load(QUrl(url))
        if boot:
            QTimer.singleShot(6300, self.close)

def main():
    if len(sys.argv)<2: raise SystemExit('Expected localhost bridge URL')
    app=QApplication(sys.argv)
    screen=app.primaryScreen().geometry()
    base=sys.argv[1].rstrip('/')
    # Two transparent surfaces within the SAME Tysm process: tiny chat/ankh and temporary boot.
    w=Overlay(base+'/overlay.html',(screen.x()+screen.width()-375,screen.y()+max(0,(screen.height()-290)//3),365,290))
    w.show()
    last_move=[0,0]
    last_side=[None]
    def sync_size():
        try:
            with urlopen(base+'/api/window',timeout=.2) as response:
                size=json.load(response)
            dx=int(size.get('move_x',0))-last_move[0]
            dy=int(size.get('move_y',0))-last_move[1]
            last_move[:]=[int(size.get('move_x',0)),int(size.get('move_y',0))]
            # Use the monitor currently containing the dock, not always the primary monitor.
            current=app.screenAt(w.geometry().center()) or app.primaryScreen()
            area=current.availableGeometry()
            if dx or dy:
                w.move(max(area.left(),min(area.right()-w.width()+1,w.x()+dx)),
                       max(area.top(),min(area.bottom()-w.height()+1,w.y()+dy)))
            target_w=max(365,min(int(size['width']),area.width()))
            target_h=max(290,min(int(size['height']),area.height()))
            # Dock is at the right edge normally. At the left edge, mirror both
            # dock and chat so the chat expands inward rather than off-screen.
            dock_x=w.x()+w.width()-60
            side='left' if dock_x < area.left()+target_w+15 else 'right'
            if side != last_side[0]:
                w.page().runJavaScript("document.documentElement.classList.toggle('dock-left',"+('true' if side=='left' else 'false')+")")
                last_side[0]=side
            if w.width()!=target_w or w.height()!=target_h:
                x=w.x() if side=='left' else w.x()+w.width()-target_w
                w.setGeometry(max(area.left(),min(area.right()-target_w+1,x)),
                              max(area.top(),min(area.bottom()-target_h+1,w.y())),target_w,target_h)
            # Keep the entire surface within the monitor's usable area.
            x=max(area.left(),min(area.right()-w.width()+1,w.x()))
            y=max(area.top(),min(area.bottom()-w.height()+1,w.y()))
            if (x,y)!=(w.x(),w.y()): w.move(x,y)
        except Exception:
            pass
    size_timer=QTimer(w);size_timer.timeout.connect(sync_size);size_timer.start(120)
    boot=Overlay(base+'/boot_overlay.html',(screen.x(),screen.y(),screen.width(),screen.height()),True)
    boot.show()
    # Preserve references until application quits.
    app._tysm_windows=(w,boot)
    sys.exit(app.exec())
if __name__=='__main__': main()
