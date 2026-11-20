import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: shell
    objectName: "deckWindow"
    width: Math.min(1260, Screen.desktopAvailableWidth)
    height: Math.min(832, Screen.desktopAvailableHeight)
    minimumWidth: 760; minimumHeight: 490
    visible: true
    title: "Scrcpy Deck"
    color: Theme.base
    background: Rectangle {
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "#101617" }
            GradientStop { position: 0.66; color: "#131b1c" }
            GradientStop { position: 1; color: "#182723" }
        }
    }
    font.family: "Nunito"; font.pixelSize: 14
    palette.window: Theme.base; palette.windowText: Theme.text; palette.text: Theme.text
    palette.button: Theme.panel; palette.buttonText: Theme.text; palette.base: Theme.input
    palette.highlight: "#619d81"; palette.highlightedText: "#ffffff"; palette.mid: Theme.line
    palette.light: "#53665f"; palette.dark: "#18211e"; palette.placeholderText: Theme.muted
    property int page: 0
    property bool narrow: width < 1040
    property bool direct: false
    property string pairPort: ""
    property string pairCode: ""
    readonly property var names: ["Connections", "Saved devices", "Display & audio", "Session controls", "Console", "Help center"]
    readonly property var glyphs: ["\ue839", "\ue8f1", "\ue7f4", "\ue9e9", "\ue756", "\ue897"]
    readonly property var pages: ["ConnectionsPage.qml", "LibraryPage.qml", "DisplayPage.qml", "ControlsPage.qml", "ConsolePage.qml", "HelpPage.qml"]
    readonly property var descriptions: [
        "Connect your Android device over USB or Wi-Fi.",
        "Reconnect to devices you have used with this computer.",
        "Set the quality, bandwidth and audio format for your stream.",
        "Choose a source and configure the behavior of your next session.",
        "Run local commands and inspect device and session output.",
        "Set up your device and find answers to common questions."
    ]
    function openQuick() { quick.active = true; quick.item.open() }
    function openEditor(i) { edit.deviceIndex = i; edit.open() }
    function askForget(i) { confirm.target = i; confirm.kind = "forget"; confirm.open() }
    function askMaintenance(kind) { confirm.kind = kind; confirm.open() }

    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillHeight: true; Layout.preferredWidth: shell.narrow ? 72 : 207
            color: Theme.rail
            Rectangle { width: 1; anchors.right: parent.right; height: parent.height; color: Theme.line }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: shell.narrow ? 10 : 16; spacing: 4
                RowLayout {
                    Layout.fillWidth: true; Layout.topMargin: 10; Layout.bottomMargin: 31
                    spacing: 10
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter; width: 37; height: 37; radius: 10; color: Theme.mint
                        Glyph { anchors.centerIn: parent; text: "\ue977"; font.pixelSize: 22; color: "#193c2c" }
                    }
                    Type { visible: !shell.narrow; text: "Scrcpy Deck"; font.pixelSize: 20; font.bold: true }
                }
                Repeater {
                    model: shell.names
                    Button {
                        id: nav; required property int index; required property string modelData
                        objectName: "nav" + index
                        Layout.fillWidth: true; Layout.preferredHeight: 42
                        Layout.topMargin: index === 4 ? 22 : 0
                        Accessible.name: modelData
                        ToolTip.visible: shell.narrow && hovered; ToolTip.text: modelData
                        onClicked: shell.page = index
                        background: Rectangle {
                            radius: 8
                            color: shell.page === nav.index ? "#294036" : nav.hovered ? "#202d29" : "transparent"
                            border.color: nav.visualFocus ? Theme.mint : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                        }
                        contentItem: RowLayout {
                            spacing: 11
                            Glyph { Layout.leftMargin: shell.narrow ? 0 : 7; Layout.fillWidth: shell.narrow; text: shell.glyphs[nav.index]; color: shell.page === nav.index ? Theme.mint : Theme.muted; font.pixelSize: 17 }
                            Type { visible: !shell.narrow; Layout.fillWidth: true; text: nav.modelData; font.bold: shell.page === nav.index; color: shell.page === nav.index ? Theme.mint : Theme.muted }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                DeckButton {
                    visible: !!deck.state.update; Layout.fillWidth: true
                    text: shell.narrow ? "↓" : "Update " + deck.state.update
                    onClicked: Qt.openUrlExternally("https://exposureee.in/scrcpy-gui-by-exposureee/")
                }
                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.line }
                Type { visible: !shell.narrow; Layout.topMargin: 9; text: "EXPOSUREEE"; font.bold: true; font.letterSpacing: 1.1; font.pixelSize: 11; quiet: true }
                Type { text: "v" + deck.version; font.family: Theme.mono; font.pixelSize: 11; quiet: true }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            RowLayout {
                Layout.fillWidth: true; Layout.margins: shell.narrow ? 18 : 26; spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 2
                    Type { text: shell.names[shell.page]; font.pixelSize: 30; font.bold: true }
                    Type { Layout.fillWidth: true; text: shell.descriptions[shell.page]; quiet: true }
                }
                DeckButton { glyph: "\ue713"; Accessible.name: "Quick settings"; ToolTip.visible: hovered; ToolTip.text: "Quick settings"; objectName: "quickButton"; onClicked: shell.openQuick() }
                DeckButton {
                    primary: true; glyph: "\ue768"; text: "Start session"
                    enabled: !deck.state.busy && (!!deck.state.serial || (deck.settings.source === "screen" && deck.settings.screen_mode === "OTG"))
                    onClicked: deck.launch()
                }
            }
            Rectangle {
                visible: !!deck.state.error
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 10
                implicitHeight: message.implicitHeight + 16; radius: 7; color: "#412d29"
                Type { id: message; x: 12; y: 8; width: parent.width - 24; maximumLineCount: 4; elide: Text.ElideRight; text: deck.state.error; color: Theme.danger }
            }
            Loader {
                id: loader; objectName: "pageLoader"
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.leftMargin: shell.narrow ? 18 : 26; Layout.rightMargin: shell.narrow ? 10 : 14
                Layout.bottomMargin: 12
                source: shell.pages[shell.page]
                onLoaded: entrance.restart()
                NumberAnimation { id: entrance; target: loader; property: "opacity"; from: 0.55; to: 1; duration: 160 }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: 34; color: "#151e1e"
                Rectangle { width: parent.width; height: 1; color: Theme.line }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 24; spacing: 9
                    Rectangle { width: 7; height: 7; radius: 4; color: deck.state.error || deck.state.busy ? Theme.amber : deck.state.serial ? Theme.mint : Theme.muted }
                    Type { Layout.fillWidth: true; text: deck.state.status; quiet: true; font.pixelSize: 12; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    DeckButton { visible: deck.state.recovering; text: "Cancel recovery"; compact: true; onClicked: deck.cancelRecovery() }
                    Type { text: deck.state.sessions + (deck.state.sessions === 1 ? " active session" : " active sessions"); font.family: Theme.mono; font.pixelSize: 11; quiet: true }
                }
            }
        }
    }
    Loader { id: quick; active: false; sourceComponent: Component { QuickDialog {} } }
    EditDialog { id: edit }
    DeckDialog {
        id: confirm
        height: Math.max(196, details.implicitHeight + 118)
        property string kind: ""
        property int target: -1
        title: kind === "forget" ? "Forget saved device?" : kind === "reset" ? "Reset ADB authorization?" : "Stop the ADB server?"
        standardButtons: Dialog.Cancel | Dialog.Ok
        Type {
            id: details; width: confirm.availableWidth
            text: confirm.kind === "forget" ? "Remove this device from your library. Scanning it again will add it back."
                  : confirm.kind === "reset" ? "This disconnects all ADB transports, removes this Windows user's ADB keys and restarts ADB. Devices will ask for authorization again."
                  : "This disconnects devices and affects other applications using this ADB server."
        }
        onAccepted: { if (kind === "forget") deck.forget(target); else deck.maintenance(kind === "reset") }
    }
    DeckDialog {
        id: recovery
        property int target: -1
        title: "Reconnect saved phone"
        ColumnLayout {
            width: parent.width; spacing: 16
            Type { Layout.fillWidth: true; text: "Check the saved address, or connect the same phone by USB and allow debugging. Recovery reads its current Wi-Fi address and reconnects on port 5555." }
            Flow {
                Layout.fillWidth: true; spacing: 6
                DeckButton { text: "Edit address"; onClicked: { recovery.close(); shell.openEditor(recovery.target) } }
                DeckButton { text: "Find on Wi-Fi"; visible: !!(deck.saved[recovery.target] || {}).hardware_serial; onClicked: { recovery.close(); deck.findSaved(recovery.target) } }
                DeckButton { primary: true; text: "Recover over USB"; onClicked: { recovery.close(); deck.recover(recovery.target) } }
            }
        }
    }
    Connections {
        target: deck
        function onRecoveryOffered(index) { recovery.target = index; recovery.open() }
        function onPaired() { shell.pairCode = "" }
    }
    Shortcut { sequence: "Ctrl+,"; onActivated: shell.openQuick() }
    Shortcut { sequence: "F5"; onActivated: deck.scan() }
}
