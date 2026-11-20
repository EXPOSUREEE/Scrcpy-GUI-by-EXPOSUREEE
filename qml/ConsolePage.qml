import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        Field {
            id: input; objectName: "commandField"; Layout.fillWidth: true
            placeholderText: "adb devices -l"; Accessible.name: "Console command"
            function run() { if (text.trim()) { deck.runCommand(text); clear() } }
            onAccepted: run()
        }
        DeckButton { text: "Run"; primary: true; onClicked: input.run() }
        DeckButton { text: "Copy log"; onClicked: deck.copy(consoleLog.transcript()) }
        DeckButton { text: "Clear"; onClicked: consoleLog.clear() }
    }
    Rectangle {
        Layout.fillWidth: true; Layout.fillHeight: true; color: Theme.input
        border.color: Theme.line; radius: 10
        ListView {
            id: list; anchors.fill: parent; anchors.margins: 12; clip: true; model: consoleLog
            spacing: 4; ScrollBar.vertical: ScrollBar {}
            property bool follow: true
            onMovementEnded: follow = atYEnd
            onCountChanged: if (follow) Qt.callLater(positionViewAtEnd)
            Component.onCompleted: positionViewAtEnd()
            delegate: Type {
                required property string line; required property string severity
                width: list.width - 14; text: line; wrapMode: Text.WrapAnywhere
                font.family: Theme.mono; font.pixelSize: 12
                color: severity === "ERR" || severity === "ERROR" ? Theme.danger : severity === "HINT" ? Theme.mint : severity === "WARN" ? Theme.amber : severity === "INFO" ? Theme.muted : Theme.text
            }
        }
    }
    Type { quiet: true; text: "Commands run in the application folder through the Windows command shell."; font.pixelSize: 12 }
}
