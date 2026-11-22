import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ComboBox {
    id: box
    property string menuLabel: ""
    property int menuRowHeight: 38
    implicitHeight: 38
    leftPadding: 12
    rightPadding: 29
    background: Rectangle {
        radius: 10
        color: box.down ? Theme.pressed : box.hovered ? Theme.hover : Theme.input
        border.color: box.activeFocus ? Theme.accent : Theme.controlLine
        border.width: box.activeFocus ? 2 : 1
    }
    contentItem: Type { text: box.displayText; elide: Text.ElideRight; wrapMode: Text.NoWrap }
    indicator: Glyph {
        name: "chevron"; size: 14; color: Theme.muted
        x: box.width - width - 12; anchors.verticalCenter: parent.verticalCenter
        rotation: box.popup.visible ? 180 : 0
        Behavior on rotation { NumberAnimation { duration: 120 } }
    }
    popup: Popup {
        id: menu
        objectName: box.objectName + "Menu"
        y: box.height + 6
        width: box.width
        implicitHeight: menuList.implicitHeight + topPadding + bottomPadding
        topMargin: 8
        bottomMargin: 8
        padding: 5
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 100 }
            NumberAnimation { property: "scale"; from: 0.98; to: 1; duration: 100 }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 80 } }
        background: Rectangle {
            objectName: box.objectName + "MenuSurface"
            radius: 12
            color: Theme.panel
            border.color: Theme.controlLine
        }
        contentItem: ListView {
            id: menuList
            clip: true
            implicitHeight: Math.min((box.menuLabel ? 34 : 0)
                                     + box.count * box.menuRowHeight
                                     + Math.max(0, box.count - 1) * spacing, 316)
            model: menu.visible ? box.delegateModel : null
            currentIndex: box.highlightedIndex
            spacing: 2
            header: Item {
                width: menuList.width
                height: box.menuLabel ? 34 : 0
                visible: height > 0
                Type {
                    x: 8; width: parent.width - 16; height: 27
                    text: box.menuLabel
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    quiet: true
                    elide: Text.ElideRight
                    wrapMode: Text.NoWrap
                }
                Rectangle {
                    width: parent.width - 8; height: 1
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    color: Theme.line
                }
            }
            ScrollIndicator.vertical: ScrollIndicator { }
        }
    }
    delegate: DropdownItem {
        required property int index
        objectName: box.objectName + "Option" + index
        width: box.popup.availableWidth
        label: box.textAt(index)
        selected: box.currentIndex === index
        highlighted: box.highlightedIndex === index
    }
}
