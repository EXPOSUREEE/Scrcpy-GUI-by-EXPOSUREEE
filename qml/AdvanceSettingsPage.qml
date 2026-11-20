import QtQuick
import QtQuick.Layouts

Sheet {
    id: page
    columns: width >= 800 ? 2 : 1
    ColumnLayout {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: page.contentSpacing
        Card {
            title: "Capture source"; glyph: "video"
            Option { label: "Source"; setting: "source"; options: Theme.sourceNames; values: Theme.sources }
            Option { label: "Screen connection"; setting: "screen_mode"; options: Theme.inputModes; values: Theme.inputValues }
        }
        Card {
            title: "Device behavior"; glyph: "hand"
            Toggle { text: "Read-only mirroring"; setting: "no_control" }
            Toggle { text: "Keep device awake"; setting: "stay_awake"; enabled: !deck.settings.no_control }
            Toggle { text: "Turn off the physical screen"; setting: "screen_off"; enabled: !deck.settings.no_control }
            Toggle { text: "Show touch points"; setting: "show_touches"; enabled: !deck.settings.no_control }
        }
        Card {
            title: "Recording & diagnostics"; glyph: "record"
            Toggle { text: "Record session to MP4"; setting: "record" }
            Toggle { text: "Open external debug console"; setting: "debug_mode" }
        }
        Card {
            title: "Screen quality"; glyph: "monitor"
            ScreenOptions {}
        }
    }
    ColumnLayout {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: page.contentSpacing
        Card {
            title: "Mirror window"; glyph: "window"
            Option { label: "Capture orientation"; setting: "orientation"; options: Theme.orientations }
            Toggle { text: "Always on top"; setting: "always_on_top" }
            Toggle { text: "Fullscreen"; setting: "fullscreen" }
            Toggle { text: "Borderless window"; setting: "borderless" }
        }
        Card {
            title: "Encoding & rendering"; glyph: "chip"
            Option { label: "Video codec"; setting: "video_codec"; options: ["h264", "h265", "av1"] }
            Option { label: "Mirror render driver"; setting: "renderer"; options: ["auto", "direct3d", "opengl", "metal", "software"] }
        }
        Card {
            title: "Audio forwarding"; glyph: "audio"
            AudioOptions {}
        }
        Card {
            title: "Camera"; glyph: "camera"
            CameraOptions {}
        }
    }
}
