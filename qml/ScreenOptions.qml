import QtQuick
import QtQuick.Layouts
ColumnLayout {
    Layout.fillWidth: true; spacing: 10
    Limiter { label: "Video bitrate"; setting: "bitrate"; low: 1; high: 64; unit: "Mbps" }
    Limiter { label: "Frame rate limit"; setting: "max_fps"; high: 120; unit: "fps" }
    Limiter { label: "Maximum size"; setting: "max_size"; high: 2560; unit: "px"; zero: "Native size" }
}
