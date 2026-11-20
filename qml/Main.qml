import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: shell
    objectName: "deckWindow"
    readonly property int captionHeight: Qt.platform.os === "windows" ? 30 : 0
    readonly property int workspaceHeight: height - captionHeight
    flags: captionHeight > 0 ? Qt.Window | Qt.CustomizeWindowHint | Qt.WindowSystemMenuHint
                               | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint : Qt.Window
    // The work area includes space for the native window frame.
    width: Math.min(1260, Screen.desktopAvailableWidth - 16)
    height: Math.min(832, Screen.desktopAvailableHeight - 40) + captionHeight
    minimumWidth: 760; minimumHeight: 420 + captionHeight
    visible: true
    title: "Scrcpy Deck"
    color: Theme.base
    font.family: Theme.sans; font.pixelSize: 13
    palette.window: Theme.base; palette.windowText: Theme.text; palette.text: Theme.text
    palette.button: Theme.panel; palette.buttonText: Theme.text; palette.base: Theme.input
    palette.highlight: Theme.accentFill; palette.highlightedText: Theme.accentText
    palette.mid: Theme.controlLine; palette.midlight: Theme.hover
    palette.light: Theme.panel; palette.dark: Theme.controlLine; palette.placeholderText: Theme.muted
    palette.toolTipBase: Theme.panel; palette.toolTipText: Theme.text
    palette.link: Theme.accent
    property int page: 0
    readonly property bool narrow: width < 980
    readonly property int gutter: narrow ? 18 : 26
    readonly property bool shortWindow: workspaceHeight < 540
    readonly property bool compactConnections: page === 0 && workspaceHeight < 720
    readonly property bool connectionErrorInFooter: page === 0 && shortWindow && !!deck.state.error
    property bool direct: false
    property string pairPort: ""
    property string pairCode: ""
    readonly property var names: ["Connections", "Saved devices", "Advance settings", "Console", "Help center"]
    readonly property var glyphs: ["link", "devices", "sliders", "terminal", "help"]
    readonly property var pages: ["ConnectionsPage.qml", "LibraryPage.qml", "AdvanceSettingsPage.qml", "ConsolePage.qml", "HelpPage.qml"]
    readonly property var descriptions: [
        "",
        "Reconnect to devices you have used with this computer.",
        "Configure capture source, stream quality, audio and session behavior.",
        "Run local commands and inspect device and session output.",
        "Set up your device and find answers to common questions."
    ]
    function openQuick() { quick.active = true; quick.item.open() }
    function openEditor(i) { edit.deviceIndex = i; edit.open() }
    function askForget(i) { confirm.target = i; confirm.kind = "forget"; confirm.open() }
    function askMaintenance(kind) { confirm.kind = kind; confirm.open() }

    header: Loader {
        active: shell.captionHeight > 0
        visible: active
        height: shell.captionHeight
        z: Overlay.overlay.z + 1
        sourceComponent: WindowCaption { targetWindow: shell }
    }

    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillHeight: true; Layout.preferredWidth: shell.narrow ? 64 : 184
            color: Theme.rail
            Rectangle { width: 1; anchors.right: parent.right; height: parent.height; color: Theme.line }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: shell.narrow ? 10 : 12; spacing: 5
                RowLayout {
                    Layout.alignment: shell.narrow ? Qt.AlignHCenter : Qt.AlignLeft
                    Layout.leftMargin: shell.narrow ? 0 : 5
                    Layout.topMargin: 8; Layout.bottomMargin: shell.shortWindow ? 10 : 23
                    spacing: 10
                    Rectangle {
                        implicitWidth: 36; implicitHeight: 36; radius: 12; color: Theme.accentFill
                        Glyph { anchors.centerIn: parent; name: "deck"; color: Theme.accentText; size: 22 }
                    }
                    Type { visible: !shell.narrow; text: "Scrcpy Deck"; font.pixelSize: 17; font.bold: true }
                }
                Repeater {
                    model: shell.names
                    Button {
                        id: nav; required property int index; required property string modelData
                        objectName: "nav" + index
                        readonly property bool selected: shell.page === index
                        Layout.fillWidth: true; Layout.preferredHeight: shell.shortWindow ? 36 : 42
                        Layout.topMargin: index === 3 ? (shell.shortWindow ? 10 : 22) : 0
                        leftPadding: shell.narrow ? 0 : 11
                        rightPadding: leftPadding
                        hoverEnabled: true
                        Accessible.name: modelData
                        Accessible.selected: selected
                        ToolTip.visible: shell.narrow && hovered; ToolTip.text: modelData
                        onClicked: shell.page = index
                        background: Rectangle {
                            radius: shell.narrow ? height / 2 : 11
                            color: nav.selected ? (shell.narrow ? Theme.accentFill : Theme.accentSoft)
                                                : nav.hovered ? Theme.hover : "transparent"
                            border.color: nav.visualFocus ? Theme.accent : "transparent"
                            border.width: nav.visualFocus ? 2 : 1
                        }
                        contentItem: RowLayout {
                            spacing: 11
                            Glyph {
                                Layout.fillWidth: shell.narrow; name: shell.glyphs[nav.index]; size: 18
                                color: nav.selected ? (shell.narrow ? Theme.accentText : Theme.accent) : Theme.muted
                            }
                            Type {
                                visible: !shell.narrow; Layout.fillWidth: true; text: nav.modelData
                                font.weight: nav.selected ? Font.DemiBold : Font.Medium
                                color: nav.selected ? Theme.accent : Theme.muted
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                DeckButton {
                    visible: !!deck.state.update; Layout.fillWidth: true
                    primary: true
                    glyph: "download"
                    text: shell.narrow ? "" : (deck.state.updateStatus === "downloading" ? ("Downloading " + deck.state.updateProgress + "%")
                                             : deck.state.updateStatus === "installing" ? "Restarting…"
                                             : ("Update " + deck.state.update))
                    enabled: deck.state.updateStatus !== "installing"
                    Accessible.name: "Update Scrcpy Deck to v" + deck.state.update
                    ToolTip.visible: shell.narrow && hovered; ToolTip.text: Accessible.name
                    onClicked: updateDialog.open()
                }
                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.line }
                Type { visible: !shell.narrow; Layout.topMargin: 6; Layout.leftMargin: 5; text: "EXPOSUREEE"; font.weight: Font.DemiBold; font.pixelSize: 11; quiet: true }
                Type { Layout.alignment: shell.narrow ? Qt.AlignHCenter : Qt.AlignLeft; Layout.leftMargin: shell.narrow ? 0 : 5; text: "v" + deck.version; font.pixelSize: 11; quiet: true }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            RowLayout {
                Layout.fillWidth: true; Layout.margins: shell.gutter; spacing: 9
                Layout.topMargin: shell.compactConnections ? (shell.shortWindow ? 8 : 12) : Layout.margins
                Layout.bottomMargin: Layout.topMargin
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 2
                    Type { Layout.fillWidth: true; text: shell.names[shell.page]; font.pixelSize: shell.compactConnections ? 24 : 30; font.letterSpacing: -0.65; font.weight: Font.DemiBold }
                    Type { Layout.fillWidth: true; visible: !!text; text: shell.descriptions[shell.page]; quiet: true }
                }
                DeckButton {
                    objectName: "appearanceButton"
                    glyph: Theme.dark ? "sun" : "moon"; compact: shell.compactConnections
                    Accessible.name: Theme.dark ? "Switch to light mode" : "Switch to dark mode"
                    ToolTip.visible: hovered; ToolTip.text: Accessible.name
                    onClicked: deck.configure("appearance", Theme.dark ? "light" : "dark")
                }
                DeckButton {
                    primary: true; glyph: "play"; text: "Start session"; compact: shell.compactConnections
                    enabled: !deck.state.busy && (!!deck.state.serial || (deck.settings.source === "screen" && deck.settings.screen_mode === "OTG"))
                    onClicked: deck.launch()
                }
            }
            Rectangle {
                id: updateBanner
                visible: !!deck.state.update && deck.state.updateStatus !== "installing"
                Layout.fillWidth: true; Layout.leftMargin: shell.gutter; Layout.rightMargin: shell.gutter
                Layout.bottomMargin: 10
                implicitHeight: 46
                radius: 10
                color: Theme.accentSoft
                border.color: Theme.accent
                border.width: 1
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14; spacing: 10
                    Glyph { name: "download"; size: 18; color: Theme.accent }
                    Type {
                        Layout.fillWidth: true; font.weight: Font.DemiBold
                        text: deck.state.updateStatus === "downloading"
                              ? ("Downloading update v" + deck.state.update + " (" + deck.state.updateProgress + "%)…")
                              : deck.state.updateStatus === "error"
                              ? ("Update failed: " + (deck.state.updateError || "Could not download"))
                              : ("Update available: Scrcpy Deck v" + deck.state.update)
                        color: Theme.text
                    }
                    DeckButton {
                        visible: deck.state.updateStatus !== "downloading"
                        primary: true; compact: true
                        text: "Install Update"
                        onClicked: deck.installUpdate()
                    }
                    DeckButton {
                        visible: deck.state.updateStatus === "downloading"
                        compact: true
                        text: "Cancel"
                        onClicked: deck.cancelUpdate()
                    }
                    DeckButton {
                        compact: true
                        text: "Details"
                        onClicked: updateDialog.open()
                    }
                }
            }
            Rectangle {
                visible: !!deck.state.error && !shell.connectionErrorInFooter
                Layout.fillWidth: true; Layout.leftMargin: shell.gutter; Layout.rightMargin: shell.gutter
                Layout.bottomMargin: 10
                implicitHeight: errorContent.implicitHeight + (shell.compactConnections ? 8 : 16)
                radius: 10; color: Theme.dangerSoft
                RowLayout {
                    id: errorContent
                    width: parent.width - 24; x: 12; anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    Type { id: message; Layout.fillWidth: true; maximumLineCount: shell.compactConnections ? 2 : 4; wrapMode: Text.Wrap; elide: Text.ElideRight; text: deck.state.error; color: Theme.danger }
                    DeckButton { visible: shell.page === 0; compact: true; text: "Open console"; onClicked: shell.page = 3 }
                }
                HoverHandler { id: errorHover }
                ToolTip.visible: errorHover.hovered && message.truncated
                ToolTip.text: deck.state.error
            }
            Loader {
                id: loader; objectName: "pageLoader"
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.leftMargin: shell.gutter; Layout.rightMargin: shell.gutter
                Layout.bottomMargin: shell.compactConnections && shell.shortWindow ? 6 : 12
                source: shell.pages[shell.page]
                onLoaded: entrance.restart()
                NumberAnimation { id: entrance; target: loader; property: "opacity"; from: 0.55; to: 1; duration: 160 }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: shell.shortWindow ? 34 : 42; color: Theme.rail
                Rectangle { width: parent.width; height: 1; color: Theme.line }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: shell.gutter; anchors.rightMargin: shell.gutter; spacing: 9
                    Rectangle { width: 7; height: 7; radius: 4; color: deck.state.error ? Theme.danger : deck.state.busy ? Theme.amber : deck.state.serial ? Theme.positive : Theme.muted }
                    Type {
                        id: statusText
                        Layout.fillWidth: true; quiet: true; font.pixelSize: 12; elide: Text.ElideRight; wrapMode: Text.NoWrap
                        text: shell.connectionErrorInFooter ? deck.state.error : deck.state.status
                        color: shell.connectionErrorInFooter ? Theme.danger : Theme.muted
                        HoverHandler { id: statusHover }
                        ToolTip.visible: shell.connectionErrorInFooter && statusText.truncated && statusHover.hovered
                        ToolTip.text: statusText.text
                    }
                    DeckButton { visible: deck.state.recovering; text: "Cancel recovery"; compact: true; onClicked: deck.cancelRecovery() }
                    DeckButton { visible: shell.connectionErrorInFooter; text: "Open console"; compact: true; Layout.preferredHeight: 28; onClicked: shell.page = 3 }
                    DeckButton {
                        id: adbUtilitiesButton
                        objectName: "adbUtilitiesButton"
                        visible: shell.page === 0; compact: true; text: "ADB utilities"; glyph: "tools"
                        Layout.preferredHeight: 28
                        onClicked: adbUtilities.open()
                    }
                    Type { text: deck.state.sessions + (deck.state.sessions === 1 ? " active session" : " active sessions"); font.pixelSize: 12; quiet: true }
                }
            }
        }
    }
    Loader { id: quick; active: false; sourceComponent: Component { QuickDialog {} } }
    EditDialog { id: edit }
    Popup {
        id: adbUtilities
        parent: adbUtilitiesButton
        x: parent.width - width
        y: -height - 8
        width: 306
        padding: 14
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            id: adbUtilitiesPanel
            objectName: "adbUtilitiesPanel"
            radius: 16
            color: Theme.panel
            border.color: Theme.controlLine
        }

        contentItem: ColumnLayout {
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    implicitWidth: 34; implicitHeight: 34; radius: 11
                    color: Theme.accentSoft
                    Glyph { anchors.centerIn: parent; name: "tools"; size: 17; color: Theme.accent }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 1
                    Type { text: "ADB utilities"; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Type { text: "Connection maintenance"; font.pixelSize: 11; quiet: true }
                }
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.line }
            Repeater {
                model: [
                    { kind: "stop", title: "Stop ADB server", detail: "End the shared background service", glyph: "circle" },
                    { kind: "reset", title: "Reset connections", detail: "Clear authorization and start fresh", glyph: "refresh" }
                ]
                DropdownItem {
                    id: utilityAction
                    required property int index
                    required property var modelData
                    readonly property bool destructive: modelData.kind === "reset"
                    readonly property color tone: destructive ? Theme.danger : Theme.amber
                    readonly property color toneSoft: destructive ? Theme.dangerSoft : Theme.amberSoft
                    objectName: modelData.kind === "reset" ? "adbResetButton" : "adbStopButton"
                    label: modelData.title
                    detail: modelData.detail
                    glyph: modelData.glyph
                    trailingGlyph: "arrow"
                    glyphColor: tone
                    glyphBackground: toneSoft
                    Layout.fillWidth: true
                    enabled: !deck.state.busy
                    onClicked: {
                        adbUtilities.close()
                        shell.askMaintenance(modelData.kind)
                    }
                }
            }
        }
    }
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
    DeckDialog {
        id: updateDialog
        title: "Software Update"
        ColumnLayout {
            width: parent.width; spacing: 14
            Type {
                Layout.fillWidth: true
                text: "A newer version of Scrcpy Deck (v" + deck.state.update + ") is available.\nCurrent version: v" + deck.version
                color: Theme.text
            }
            Rectangle {
                visible: deck.state.updateStatus === "downloading"
                Layout.fillWidth: true; implicitHeight: 8; radius: 4; color: Theme.input
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(1, (deck.state.updateProgress || 0) / 100))
                    height: parent.height; radius: 4; color: Theme.accentFill
                }
            }
            Type {
                visible: deck.state.updateStatus === "downloading"
                Layout.fillWidth: true; quiet: true
                text: "Downloading update… " + deck.state.updateProgress + "%"
            }
            Type {
                visible: deck.state.updateStatus === "installing"
                Layout.fillWidth: true; quiet: true
                text: "Installing update and restarting Scrcpy Deck…"
            }
            Type {
                visible: deck.state.updateStatus === "error"
                Layout.fillWidth: true; color: Theme.danger
                text: "Error: " + deck.state.updateError
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Item { Layout.fillWidth: true }
                DeckButton {
                    text: deck.state.updateStatus === "downloading" ? "Cancel" : "Close"
                    onClicked: {
                        if (deck.state.updateStatus === "downloading") deck.cancelUpdate()
                        updateDialog.close()
                    }
                }
                DeckButton {
                    visible: deck.state.updateStatus !== "downloading" && deck.state.updateStatus !== "installing"
                    primary: true
                    text: "Install Update"
                    onClicked: deck.installUpdate()
                }
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
