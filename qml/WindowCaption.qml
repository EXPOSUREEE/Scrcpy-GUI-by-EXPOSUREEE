import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Window

Rectangle {
    id: caption
    objectName: "windowCaption"
    required property Window targetWindow
    readonly property bool maximized: targetWindow.visibility === Window.Maximized
    color: Theme.dark ? "#101014" : Theme.rail

    function toggleMaximized() {
        if (maximized)
            targetWindow.showNormal()
        else
            targetWindow.showMaximized()
    }

    Item {
        id: titleArea
        anchors.left: parent.left
        anchors.right: controls.left
        height: parent.height

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 7
            Image {
                width: 14; height: 14
                source: "../assets/icon.ico"
                sourceSize: Qt.size(16, 16)
                anchors.verticalCenter: parent.verticalCenter
            }
            Type {
                text: caption.targetWindow.title
                font.pixelSize: 12
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    Row {
        id: controls
        objectName: "captionControls"
        property bool nativeHover: false
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height
        HoverHandler { id: groupHover }

        CaptionButton {
            objectName: "captionMinimize"
            Accessible.name: "Minimize"
            fill: "#ffbd2e"
            mark: "M4 9H14"
            onClicked: caption.targetWindow.showMinimized()
        }
        CaptionButton {
            objectName: "captionMaximize"
            Accessible.name: caption.maximized ? "Restore" : "Maximize"
            fill: "#28c840"
            mark: caption.maximized ? "M4 7H7V4 M14 11H11V14"
                                    : "M4 10V4H10 M8 14H14V8"
            onClicked: caption.toggleMaximized()
        }
        CaptionButton {
            objectName: "captionClose"
            Accessible.name: "Close"
            fill: "#ff6058"
            mark: "M5 5L13 13 M13 5L5 13"
            onClicked: caption.targetWindow.close()
        }
    }

    component CaptionButton: Button {
        id: button
        required property color fill
        required property string mark
        property bool nativePressed: false
        width: 24
        height: caption.height
        padding: 0
        background: null

        contentItem: Item {
            Rectangle {
                anchors.centerIn: parent
                width: 14; height: 14; radius: 7
                color: button.down || button.nativePressed ? Qt.darker(button.fill, 1.18) : button.fill
                border.width: button.visualFocus ? 1 : 0
                border.color: Theme.text

                Shape {
                    anchors.centerIn: parent
                    width: 18; height: 18
                    scale: 0.68
                    opacity: groupHover.hovered || controls.nativeHover || button.visualFocus ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
                    ShapePath {
                        fillColor: "transparent"
                        strokeColor: "#392514"
                        strokeWidth: 2
                        capStyle: ShapePath.RoundCap
                        joinStyle: ShapePath.RoundJoin
                        PathSvg { path: button.mark }
                    }
                }
            }
        }
    }
}
