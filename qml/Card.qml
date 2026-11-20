import QtQuick
import QtQuick.Layouts
Rectangle {
    id: card
    default property alias contents: body.data
    property string title: ""
    property string glyph: ""
    property int inset: 20
    Layout.fillWidth: true
    implicitHeight: body.implicitHeight + inset * 2
    color: Theme.panel
    border.color: Theme.line
    radius: 14
    ColumnLayout {
        id: body
        x: card.inset; y: card.inset; width: card.width - 2 * card.inset
        spacing: 12
        RowLayout {
            visible: !!card.title
            Layout.fillWidth: true
            spacing: 10
            Glyph { visible: !!card.glyph; text: card.glyph; font.pixelSize: 18 }
            Type { Layout.fillWidth: true; text: card.title; font.bold: true; font.pixelSize: 18 }
        }
    }
}
