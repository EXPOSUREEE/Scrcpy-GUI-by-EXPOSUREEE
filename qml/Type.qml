import QtQuick
Text {
    property bool quiet: false
    color: quiet ? Theme.muted : Theme.text
    font.family: "Nunito"
    font.pixelSize: 14
    textFormat: Text.PlainText
    wrapMode: Text.WordWrap
    verticalAlignment: Text.AlignVCenter
}
