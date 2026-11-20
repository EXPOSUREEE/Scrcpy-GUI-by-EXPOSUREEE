import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool primary: false
    property string glyph: ""
    property bool compact: false
    implicitHeight: compact ? 33 : 39
    implicitWidth: Math.max(40, contentItem.implicitWidth + leftPadding + rightPadding)
    leftPadding: compact ? 11 : 15
    rightPadding: leftPadding
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    contentItem: Item {
        implicitWidth: labels.implicitWidth
        Row {
            id: labels; anchors.centerIn: parent
            spacing: control.glyph && control.text ? 9 : 0
            Glyph { visible: !!control.glyph; text: control.glyph; height: 22; color: control.primary ? "#102820" : Theme.mint; font.pixelSize: 15 }
            Type { text: control.text; height: 22; font.bold: true; font.pixelSize: 13; color: control.primary ? "#102820" : Theme.text }
        }
    }
    background: Rectangle {
        radius: 8
        color: control.primary ? (control.down ? "#7ed6a6" : control.hovered ? "#c5f7d8" : Theme.mint)
                               : control.down ? "#2d3d3c" : control.hovered ? "#344540" : "#263332"
        border.color: control.visualFocus ? "white" : control.primary ? color : "#455550"
        Behavior on color { ColorAnimation { duration: 110 } }
    }
}
