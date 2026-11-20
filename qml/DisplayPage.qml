import QtQuick
import QtQuick.Layouts
Sheet {
    id: page
    columns: width >= 800 ? 2 : 1
    Card { title: "Screen quality"; glyph: "monitor"; Layout.rowSpan: page.columns; ScreenOptions {} }
    Card {
        title: "Encoding & rendering"; glyph: "chip"
        Option { label: "Video codec"; setting: "video_codec"; options: ["h264", "h265", "av1"] }
        Option { label: "Mirror render driver"; setting: "renderer"; options: ["auto", "direct3d", "opengl", "metal", "software"] }
    }
    Card { title: "Audio forwarding"; glyph: "audio"; AudioOptions {} }
}
