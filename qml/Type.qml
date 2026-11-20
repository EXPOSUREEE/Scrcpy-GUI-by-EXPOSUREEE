import QtQuick
Text {
    property bool quiet: false
    color: quiet ? Theme.muted : Theme.text
    font.family: Theme.sans
    font.pixelSize: 13
    textFormat: Text.PlainText
    wrapMode: Text.WordWrap
    verticalAlignment: Text.AlignVCenter
}
