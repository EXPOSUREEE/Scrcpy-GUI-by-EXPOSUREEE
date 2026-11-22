import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool primary: false
    property bool selected: false
    property string glyph: ""
    property bool compact: false
    implicitHeight: compact ? 33 : 38
    implicitWidth: text ? contentItem.implicitWidth + leftPadding + rightPadding : implicitHeight
    leftPadding: text ? (compact ? 11 : 15) : 0
    rightPadding: leftPadding
    hoverEnabled: true
    Accessible.selected: selected
    contentItem: Item {
        implicitWidth: labels.implicitWidth
        Row {
            id: labels; anchors.centerIn: parent
            spacing: control.glyph && control.text ? 7 : 0
            Glyph {
                visible: !!control.glyph
                name: control.glyph; size: 16; anchors.verticalCenter: parent.verticalCenter
                color: !control.enabled ? Theme.muted : control.primary ? Theme.accentText
                                       : control.selected ? Theme.accent : Theme.muted
            }
            Type {
                visible: !!control.text
                text: control.text; height: 22; font.weight: Font.DemiBold; font.pixelSize: 12
                color: !control.enabled ? Theme.muted : control.primary ? Theme.accentText
                                       : control.selected ? Theme.accent : Theme.text
            }
        }
    }
    background: Rectangle {
        radius: height / 2
        color: !control.enabled ? Theme.hover
                               : control.primary ? (control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accentFill)
                               : control.selected ? Theme.accentSoft
                               : control.down ? Theme.pressed : control.hovered ? Theme.hover : Theme.panel
        border.color: !control.enabled ? Theme.line : control.visualFocus ? Theme.accent
                                      : control.primary || control.selected ? color : Theme.controlLine
        border.width: control.visualFocus ? 2 : 1
    }
}
