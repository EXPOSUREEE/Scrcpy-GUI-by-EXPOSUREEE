import QtQuick
import QtQuick.Layouts
ColumnLayout {
    Layout.fillWidth: true; spacing: 6
    Option { label: "Audio codec"; setting: "audio_codec"; options: ["opus", "aac", "raw"] }
    Toggle { text: "Mute audio during screen mirroring"; setting: "no_audio" }
}
