"""Six-second V4-inspired overlay, with original pendant handoff and once-per-launch audio."""
import random
import time
import tkinter as tk
from pathlib import Path
from tysm_startup_intro import TysmIntroStartup

class V5Boot(TysmIntroStartup):
    DURATION = 6.0
    def start(self):
        if self.played:
            return
        self.played = True
        self._play_audio()
        try:
            self._begin()
        except Exception:
            self._finish_boot()

    def _begin(self):
        self.animator.paused = True
        self._boot_done = False
        self._started = time.monotonic()
        self._w = self.root.winfo_screenwidth()
        self._h = self.root.winfo_screenheight()
        self._key = '#ff00ff'
        self._overlay = tk.Toplevel(self.root)
        self._overlay.overrideredirect(True)
        self._overlay.attributes('-topmost', True)
        self._overlay.configure(bg=self._key)
        self._overlay.geometry(f'{self._w}x{self._h}+0+0')
        try:
            self._overlay.wm_attributes('-transparentcolor', self._key)
        except tk.TclError:
            pass
        self._canvas = tk.Canvas(self._overlay, bg=self._key, highlightthickness=0)
        self._canvas.pack(fill='both',expand=True)
        self._overlay.bind('<Escape>', lambda event: self._finish_boot())
        self._overlay.focus_force()
        self._stars = []
        self._last = time.monotonic()
        self._frame = 0
        self._boot_tick()

    def _boot_tick(self):
        if self._boot_done:
            return
        now = time.monotonic()
        t = now-self._started
        dt = min(.05, now-self._last)
        self._last = now
        if t >= self.DURATION:
            self._finish_boot()
            return
        c = self._canvas
        w,h = self._w,self._h
        c.delete('all')
        # Deliberate transparent holes reveal the *actual* desktop, not a simulation.
        c.create_rectangle(0,0,w,h,fill='#090a15',outline='')
        phase = 0 if t<1 else 1 if t<2 else 2 if t<4.1 else 3 if t<5 else 4
        labels = ['INITIALIZING SYSTEM','SIGNAL INTERRUPTION','ACCESS OVERRIDE','YOU SHOULD SMILE MORE','SYSTEM ONLINE']
        sub = ['LOADING DESKTOP ENVIRONMENT','UNKNOWN SIGNAL DETECTED','SIGNAL AUTHORITY // TYSM','SIGNATURE CONFIRMED','RETURNING TO DESKTOP']
        if t>1.2:
            for i in range(9):
                y=(i*119+self._frame*3)%h
                c.create_line(0,y,w,y,fill='#38283c')
        if t>=2:
            if self._frame%5==0 and t<4.8:
                for _ in range(2):
                    self._stars.append([random.randrange(0,w),random.randrange(-180,-10),random.randrange(650,1200),random.randrange(55,145),random.choice(['#f59bdb','#9beef0'])])
            alive=[]
            for star in self._stars:
                star[2]=min(1500,star[2]+400*dt)
                star[1]+=star[2]*dt
                x,y,speed,length,color=star
                if y-length<h:
                    c.create_rectangle(x-2,y-length,x+2,y,fill=color,outline='')
                    c.create_line(x-4,y,x+4,y,fill='#fff5fa',width=2)
                    alive.append(star)
            self._stars=alive
            for side in (0,1):
                x=random.randrange(0,max(1,w//5)) if side==0 else random.randrange(max(1,w*4//5),w)
                y=random.randrange(0,h)
                c.create_rectangle(x,y,x+random.randrange(35,140),y+2,fill=random.choice(['#ed78bc','#6ce2e9']),outline='')
        if t>4.3:
            for i in range(int((t-4.3)*38)):
                x=(i*157+self._frame*31)%w
                y=(i*103+self._frame*17)%h
                c.create_rectangle(x,y,min(w,x+95),min(h,y+30),fill=self._key,outline=self._key)
        if t>5.05:
            fraction=min(1,(t-5.05)/.85)
            c.create_rectangle(0,0,w*fraction,h,fill=self._key,outline=self._key)
            c.create_rectangle(w*(1-fraction),0,w,h,fill=self._key,outline=self._key)
        if t<5.35:
            color='#f4b6de' if phase<2 else '#f28ccf'
            c.create_text(w/2,h*.44,text=labels[phase],fill=color,font=('Consolas',22,'bold'))
            c.create_text(w/2,h*.50,text=sub[phase],fill='#a898b4',font=('Consolas',10))
            c.create_rectangle(w*.36,h*.54,w*.64,h*.545,fill='#413044',outline='')
            c.create_rectangle(w*.36,h*.54,w*(.36+.28*t/6),h*.545,fill='#e875c5',outline='')
        if 2<t<5.4:
            c.create_text(25,h-28,anchor='w',text='creator - Riko',fill='#e7a2d0',font=('Consolas',10))
        self._frame+=1
        self.root.after(33,self._boot_tick)

    def _finish_boot(self):
        if getattr(self,'_boot_done',False):
            return
        self._boot_done=True
        if hasattr(self,'_overlay'):
            try: self._overlay.destroy()
            except tk.TclError: pass
        # Original pendant and existing startup completion handler.
        self._finish()
