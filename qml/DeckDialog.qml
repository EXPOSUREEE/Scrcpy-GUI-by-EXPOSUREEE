import QtQuick
import QtQuick.Controls
Dialog {
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(480, parent.width - 48)
    modal: true; focus: true; padding: 20
    background: Rectangle { radius: 12; color: Theme.panel; border.color: "#52645b" }
    header: Type { text: parent.title; font.bold: true; font.pixelSize: 21; leftPadding: 20; topPadding: 18; rightPadding: 16 }
    Overlay.modal: Rectangle { color: "#a5081010" }
}
