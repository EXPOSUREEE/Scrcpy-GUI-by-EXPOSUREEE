import QtQuick
import QtQuick.Layouts
Rectangle {
    id: card
    default property alias contents: body.data
    property string title: ""
    property string glyph: ""
    property int inset: 18
    property alias spacing: body.spacing
    Layout.fillWidth: true
    Layout.alignment: Qt.AlignTop
    Layout.preferredWidth: 1
    implicitHeight: body.implicitHeight + inset * 2
    color: Theme.panel
    border.color: Theme.line
    radius: 16
    ColumnLayout {
        id: body
        x: card.inset; y: card.inset; width: card.width - 2 * card.inset
        spacing: 12
        RowLayout {
            visible: !!card.title
            Layout.fillWidth: true
            spacing: 10
            Rectangle {
                visible: !!card.glyph
                implicitWidth: card.inset <= 12 ? 24 : 32
                implicitHeight: implicitWidth
                radius: 9
                color: Theme.accentSoft
                Glyph { anchors.centerIn: parent; name: card.glyph; size: card.inset <= 12 ? 14 : 17 }
            }
            Type { Layout.fillWidth: true; text: card.title; font.weight: Font.DemiBold; font.pixelSize: 16 }
        }
    }
}
