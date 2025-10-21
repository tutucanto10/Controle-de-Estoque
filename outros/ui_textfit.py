# >>> INÍCIO (novo arquivo - criar ui_widgets.py)
import tkinter as tk
import customtkinter as ctk
from tkinter import font as tkfont

class CTKMarquee(ctk.CTkFrame):
    def __init__(self, master, text, width=240, height=24, speed_px=1, interval_ms=15,
                 font=None, fg_color="transparent", text_color=None, padx=4, **kwargs):
        super().__init__(master, width=width, height=height, fg_color=fg_color, **kwargs)
        self.pack_propagate(False)
        self._canvas = tk.Canvas(self, width=width, height=height, bd=0, highlightthickness=0, bg=self._resolve_bg())
        self._canvas.pack(fill="both", expand=True, padx=padx)

        self._ctk_font = font or ctk.CTkFont(size=13)
        family = self._ctk_font._font.cget("family")
        size = self._ctk_font._font.cget("size")
        weight = "bold" if "bold" in self._ctk_font._font.actual().get("weight","") else "normal"
        self._tk_font = tkfont.Font(family=family, size=size, weight=weight)

        self._text = text
        self._dir = -1
        self._speed = speed_px
        self._interval = interval_ms
        self._paused = False
        self._text_color = text_color or ctk.ThemeManager.theme["CTkLabel"]["text_color"]

        self._text_id = self._canvas.create_text(0, height//2, anchor="w",
                                                 text=self._text, fill=self._resolve_text_color(),
                                                 font=self._tk_font)
        self.after(10, self._start)
        self._canvas.bind("<Enter>", lambda e: self._pause(True))
        self._canvas.bind("<Leave>", lambda e: self._pause(False))

    def _resolve_bg(self):
        if self._fg_color == "transparent":
            try:
                return self._get_widget_master().cget("bg")
            except Exception:
                return "#2b2b2b"
        return self._fg_color

    def _resolve_text_color(self):
        return self._text_color[1] if isinstance(self._text_color, tuple) else self._text_color

    def _pause(self, v: bool): self._paused = v

    def _start(self): self._layout_and_anim()

    def _layout_and_anim(self):
        if not self.winfo_exists(): return
        self.update_idletasks()
        cw = self._canvas.winfo_width()
        tw = self._tk_font.measure(self._text)
        ch = self._canvas.winfo_height()

        if tw <= cw:
            self._canvas.coords(self._text_id, (cw - tw)//2, ch//2)
            return
        self._canvas.coords(self._text_id, 0, ch//2)
        self._dir = -1
        self._tick()

    def _tick(self):
        if not self.winfo_exists(): return
        if self._paused:
            self.after(self._interval, self._tick); return

        cw = self._canvas.winfo_width()
        tw = self._tk_font.measure(self._text)
        x, y = self._canvas.coords(self._text_id)
        x_next = x + (self._dir * self._speed)
        left_limit = -(tw - cw); right_limit = 0

        if x_next < left_limit:
            x_next = left_limit; self._dir = +1
        elif x_next > right_limit:
            x_next = right_limit; self._dir = -1

        self._canvas.coords(self._text_id, x_next, y)
        self.after(self._interval, self._tick)

def render_cell(parent, text, max_width, font=None, **label_kwargs):
    """Se couber, CTkLabel; se não, CTKMarquee no mesmo tamanho."""
    tmp_font = font or ctk.CTkFont(size=13)
    tkf = tkfont.Font(family=tmp_font._font.cget("family"),
                      size=tmp_font._font.cget("size"),
                      weight="bold" if "bold" in tmp_font._font.actual().get("weight","") else "normal")
    if tkf.measure(text) <= max_width:
        return ctk.CTkLabel(parent, text=text, font=tmp_font, **label_kwargs)
    return CTKMarquee(parent, text=text, width=max_width, height=24, font=tmp_font,
                      text_color=label_kwargs.get("text_color"))
# <<< FIM