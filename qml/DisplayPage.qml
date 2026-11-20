import QtQuick
Sheet {
    Card { title: "Screen quality"; glyph: "\ue7f4"; ScreenOptions {} }
    Card {
        title: "Encoding & rendering"; glyph: "\ue950"
        Option { label: "Video codec"; setting: "video_codec"; options: ["h264", "h265", "av1"] }
        Option { label: "Mirror render driver"; setting: "renderer"; options: ["auto", "direct3d", "opengl", "metal", "software"] }
    }
    Card { title: "Audio forwarding"; glyph: "\ue767"; AudioOptions {} }
}
