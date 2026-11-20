import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ItemDelegate {
    id: control
    property string label: ""
    property string detail: ""
    property string shortcut: ""
    property string glyph: ""
    property string trailingGlyph: ""
    property bool selected: false
    property color glyphColor: Theme.accent
    property color glyphBackground: Theme.accentSoft

    text: label
    implicitHeight: detail ? 52 : 38
    leftPadding: 9
    rightPadding: 9
    hoverEnabled: true
    Accessible.name: label
    Accessible.selected: selected

    contentItem: RowLayout {
        spacing: 9
        Rectangle {
            visible: !!control.glyph
            implicitWidth: 32; implicitHeight: 32; radius: 9
            color: control.enabled ? control.glyphBackground : Theme.hover
            Glyph {
                anchors.centerIn: parent
                name: control.glyph
                size: 15
                color: control.enabled ? control.glyphColor : Theme.muted
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Type {
                Layout.fillWidth: true
                text: control.label
                font.pixelSize: 12
                font.weight: control.selected ? Font.DemiBold : Font.Medium
                color: !control.enabled ? Theme.muted : control.selected ? Theme.accent : Theme.text
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
            }
            Type {
                visible: !!control.detail
                Layout.fillWidth: true
                text: control.detail
                font.pixelSize: 10
                quiet: true
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
            }
        }
        Type {
            visible: !!control.shortcut
            text: control.shortcut
            quiet: true
            font.pixelSize: 10
            wrapMode: Text.NoWrap
        }
        Glyph {
            visible: control.selected || !!control.trailingGlyph
            name: control.selected ? "check" : control.trailingGlyph
            size: 14
            color: control.selected ? Theme.accent : Theme.muted
        }
    }

    background: Rectangle {
        radius: 8
        color: !control.enabled ? "transparent"
              : control.down ? Theme.pressed
              : control.selected ? Theme.accentSoft
              : control.highlighted || control.hovered ? Theme.hover : "transparent"
        border.color: control.visualFocus ? Theme.accent : "transparent"
        border.width: control.visualFocus ? 2 : 1
    }
}
