import QtQuick
import QtQuick.Layouts
Sheet {
    Card {
        title: "Capture source"; glyph: "\ue714"
        Option { label: "Source"; setting: "source"; options: Theme.sourceNames; values: Theme.sources }
        Option { label: "Screen connection"; setting: "screen_mode"; options: Theme.inputModes; values: Theme.inputValues }
    }
    Card {
        title: "Mirror window"; glyph: "\ue737"
        Option { label: "Capture orientation"; setting: "orientation"; options: Theme.orientations }
        Toggle { text: "Always on top"; setting: "always_on_top" }
        Toggle { text: "Fullscreen"; setting: "fullscreen" }
        Toggle { text: "Borderless window"; setting: "borderless" }
    }
    Card {
        title: "Device behavior"; glyph: "\ue8ea"
        Toggle { text: "Read-only mirroring"; setting: "no_control" }
        Toggle { text: "Keep device awake"; setting: "stay_awake"; enabled: !deck.settings.no_control }
        Toggle { text: "Turn off the physical screen"; setting: "screen_off"; enabled: !deck.settings.no_control }
        Toggle { text: "Show touch points"; setting: "show_touches"; enabled: !deck.settings.no_control }
    }
    Card { title: "Camera"; glyph: "\ue722"; CameraOptions {} }
    Card {
        title: "Recording & diagnostics"; glyph: "\ue7c8"
        Toggle { text: "Record session to MP4"; setting: "record" }
        Toggle { text: "Open external debug console"; setting: "debug_mode" }
    }
}
