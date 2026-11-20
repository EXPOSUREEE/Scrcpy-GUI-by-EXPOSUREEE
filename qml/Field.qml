import QtQuick
import QtQuick.Controls
TextField {
    id: control
    implicitHeight: 38
    leftPadding: 12
    color: Theme.text
    placeholderTextColor: "#8a9e97"
    selectByMouse: true
    selectionColor: "#3f755d"
    background: Rectangle {
        radius: 7; color: Theme.input
        border.color: control.activeFocus ? Theme.mint : Theme.line
    }
}
