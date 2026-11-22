import QtQuick
import QtQuick.Controls
TextField {
    id: control
    implicitHeight: 38
    leftPadding: 12
    font.family: Theme.sans
    font.pixelSize: 13
    color: Theme.text
    placeholderTextColor: Theme.muted
    selectByMouse: true
    selectionColor: Theme.accentFill
    selectedTextColor: Theme.accentText
    background: Rectangle {
        radius: 9; color: Theme.input
        border.color: control.activeFocus ? Theme.accent : Theme.controlLine
    }
}
