import QtQuick
import QtQuick.Controls
ComboBox {
    id: box
    implicitHeight: 38
    leftPadding: 12
    rightPadding: 29
    background: Rectangle {
        radius: 7; color: box.hovered ? "#22302c" : Theme.input
        border.color: box.visualFocus ? Theme.mint : Theme.line
    }
    contentItem: Type { text: box.displayText; elide: Text.ElideRight; wrapMode: Text.NoWrap }
    indicator: Glyph {
        text: "\ue70d"; font.pixelSize: 11
        x: box.width - width - 12; anchors.verticalCenter: parent.verticalCenter
    }
    delegate: ItemDelegate {
        required property int index
        width: box.width; height: 36
        contentItem: Type { text: box.textAt(index); elide: Text.ElideRight; wrapMode: Text.NoWrap }
        background: Rectangle { color: parent.highlighted || parent.hovered ? "#345043" : Theme.panel }
        highlighted: box.highlightedIndex === index
    }
}
