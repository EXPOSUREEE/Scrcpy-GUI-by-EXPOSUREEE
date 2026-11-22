"""Use the Windows non-client hit tests for the Qt Quick window caption."""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QMetaObject, QPointF, Qt
from PySide6.QtQuick import QQuickItem

WM_NCHITTEST = 0x0084
WM_NCDESTROY = 0x0082
WM_NCMOUSEMOVE = 0x00A0
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP = 0x00A2
WM_NCLBUTTONDBLCLK = 0x00A3
WM_MOUSEMOVE = 0x0200
WM_NCMOUSELEAVE = 0x02A2
HTCAPTION = 2
HTMAXBUTTON = 9
TME_LEAVE = 0x00000002
TME_NONCLIENT = 0x00000010
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35


class _MouseTracking(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("window", wintypes.HWND),
        ("hover_time", wintypes.DWORD),
    ]


_user32 = ctypes.WinDLL("user32")
_user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
_user32.ScreenToClient.restype = wintypes.BOOL
_user32.TrackMouseEvent.argtypes = [ctypes.POINTER(_MouseTracking)]
_user32.TrackMouseEvent.restype = wintypes.BOOL

_dwmapi = ctypes.WinDLL("dwmapi")
_dwmapi.DwmSetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
]
_dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long

_SubclassProc = ctypes.WINFUNCTYPE(
    wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    ctypes.c_size_t, ctypes.c_size_t,
)
_comctl32 = ctypes.WinDLL("comctl32")
_comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, _SubclassProc, ctypes.c_size_t, ctypes.c_size_t]
_comctl32.SetWindowSubclass.restype = wintypes.BOOL
_comctl32.RemoveWindowSubclass.argtypes = [wintypes.HWND, _SubclassProc, ctypes.c_size_t]
_comctl32.RemoveWindowSubclass.restype = wintypes.BOOL
_comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_comctl32.DefSubclassProc.restype = wintypes.LPARAM
_captions = {}


@_SubclassProc
def _caption_proc(handle, message, wparam, lparam, subclass_id, _reference):
    if message == WM_NCDESTROY:
        _comctl32.RemoveWindowSubclass(handle, _caption_proc, subclass_id)
        _captions.pop(handle, None)
    else:
        result = _captions[handle].handle_message(message, wparam, lparam)
        if result is not None:
            return result
    return _comctl32.DefSubclassProc(handle, message, wparam, lparam)


def install_windows_caption(window):
    """Attach caption hit testing and theme the native frame around the title bar."""
    caption = _WindowsCaption(window)
    _captions[caption.handle] = caption
    if not _comctl32.SetWindowSubclass(caption.handle, _caption_proc, 0, 0):
        _captions.pop(caption.handle)
        raise OSError("Could not attach the Windows caption to the Scrcpy Deck window.")
    caption.caption.colorChanged.connect(caption.sync_frame_color)
    caption.sync_frame_color()


class _WindowsCaption:
    """Enable native caption dragging and Windows Snap Layouts on the green button."""

    def __init__(self, window):
        self.window = window
        self.handle = window.winId()
        self.caption = window.findChild(QQuickItem, "windowCaption")
        self.controls = window.findChild(QQuickItem, "captionControls")
        self.maximize = window.findChild(QQuickItem, "captionMaximize")

    def sync_frame_color(self):
        """Match the non-client strip and outline to the custom caption."""
        color = self.caption.property("color")
        color_ref = wintypes.DWORD(color.red() | (color.green() << 8) | (color.blue() << 16))
        for attribute in (DWMWA_CAPTION_COLOR, DWMWA_BORDER_COLOR):
            _dwmapi.DwmSetWindowAttribute(self.handle, attribute, ctypes.byref(color_ref),
                                          ctypes.sizeof(color_ref))

    def handle_message(self, message, wparam, lparam):
        if message == WM_NCHITTEST:
            return self._hit_test(lparam)
        if message == WM_NCMOUSEMOVE:
            hover = wparam == HTMAXBUTTON
            if hover and not self.controls.property("nativeHover"):
                tracking = _MouseTracking(ctypes.sizeof(_MouseTracking), TME_LEAVE | TME_NONCLIENT,
                                          self.handle, 0)
                _user32.TrackMouseEvent(ctypes.byref(tracking))
            self._set_hover(hover)
        elif message in (WM_NCMOUSELEAVE, WM_MOUSEMOVE):
            self._set_hover(False)
        elif wparam == HTMAXBUTTON:
            # The OS recognizes the hit target for Snap Layouts. The Qt button
            # still supplies the click action and its pressed appearance.
            if message in (WM_NCLBUTTONDOWN, WM_NCLBUTTONDBLCLK):
                self.maximize.setProperty("nativePressed", True)
                return 0
            if message == WM_NCLBUTTONUP:
                if self.maximize.property("nativePressed"):
                    self.maximize.setProperty("nativePressed", False)
                    QMetaObject.invokeMethod(self.maximize, "click", Qt.QueuedConnection)
                return 0
        return None

    def _hit_test(self, screen_position):
        point = wintypes.POINT(ctypes.c_short(screen_position & 0xffff).value,
                               ctypes.c_short(screen_position >> 16).value)
        if not _user32.ScreenToClient(self.handle, ctypes.byref(point)):
            return None
        scale = self.window.devicePixelRatio()
        scene_point = QPointF(point.x / scale, point.y / scale)
        if self.maximize.contains(self.maximize.mapFromScene(scene_point)):
            return HTMAXBUTTON
        if (self.caption.contains(self.caption.mapFromScene(scene_point))
                and not self.controls.contains(self.controls.mapFromScene(scene_point))):
            return HTCAPTION
        return None

    def _set_hover(self, hover):
        self.controls.setProperty("nativeHover", hover)
        if not hover:
            self.maximize.setProperty("nativePressed", False)
