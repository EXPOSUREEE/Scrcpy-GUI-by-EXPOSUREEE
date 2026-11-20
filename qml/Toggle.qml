import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Switch {
    id: control
    property string setting
    Layout.fillWidth: true
    checked: !!deck.settings[setting]
    onToggled: deck.configure(setting, checked)
    implicitHeight: 32
    spacing: 12
    leftPadding: 0
    rightPadding: 0
    contentItem: Type { text: control.text; rightPadding: 60 }
    indicator: Rectangle {
        x: control.width - width; anchors.verticalCenter: parent.verticalCenter
        implicitWidth: 37; implicitHeight: 21; radius: height / 2
        color: control.checked ? Theme.mint : "#40504f"
        border.color: control.visualFocus ? "white" : color
        Rectangle {
            width: 15; height: 15; radius: 8; y: 3
            x: control.checked ? parent.width - width - 3 : 3
            color: control.checked ? "#183328" : "#ced9d3"
            Behavior on x { NumberAnimation { duration: 125 } }
        }
    }
}
