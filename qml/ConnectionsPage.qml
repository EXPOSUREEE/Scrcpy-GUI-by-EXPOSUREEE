import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Sheet {
    id: page
    objectName: "connectionsPage"
    readonly property var window: ApplicationWindow.window
    readonly property var ready: deck.state.devices.filter(d => d.state === "device")
    readonly property var current: ready.find(d => d.serial === deck.state.serial)
    readonly property bool wireless: current ? current.transport === "wireless" : false
    readonly property var blocked: deck.state.devices.find(d => d.state !== "device")
    readonly property bool compact: window.compactConnections
    readonly property int cardInset: window.shortWindow ? 12 : compact ? 16 : 18
    readonly property int cardSpacing: window.shortWindow ? 4 : compact ? 8 : 12
    readonly property bool otg: deck.settings.source === "screen" && deck.settings.screen_mode === "OTG"
    readonly property bool camera: deck.settings.source.startsWith("camera")
    readonly property bool mic: deck.settings.source === "mic_only"
    readonly property string fps: (camera ? deck.settings.camera_fps : deck.settings.max_fps) || "0"
    readonly property string sizeLimit: (camera ? deck.settings.camera_max_size : deck.settings.max_size) || "0"
    contentSpacing: compact ? 10 : 14

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: Math.max(page.compact ? 0 : 164, hero.implicitHeight + (page.window.shortWindow ? 18 : 36))
        radius: 16; color: Theme.panel; border.color: Theme.line
        SignalArt {
            width: page.compact ? 0 : Math.min(parent.width * 0.31, 310)
            height: parent.height - 24
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            visible: !page.compact
            connected: !!page.current
            wireless: page.wireless
        }
        GridLayout {
            id: hero
            anchors.left: parent.left; anchors.leftMargin: page.cardInset
            anchors.verticalCenter: parent.verticalCenter
            width: page.compact ? parent.width - 2 * page.cardInset : parent.width * 0.67 - 26
            columns: page.compact ? 2 : 1; columnSpacing: 12; rowSpacing: 10
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Rectangle {
                    visible: !page.compact
                    implicitWidth: connectionLabel.implicitWidth + 16; implicitHeight: 22
                    radius: 11
                    color: page.current ? Theme.positiveSoft : page.blocked ? Theme.amberSoft : Theme.hover
                    Row {
                        id: connectionLabel
                        anchors.centerIn: parent
                        spacing: 5
                        Rectangle {
                            width: 5; height: 5; radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: connectionStatus.color
                        }
                        Type {
                            id: connectionStatus
                            text: page.current ? (page.wireless ? "Connected over Wi-Fi" : "Connected over USB")
                                               : page.blocked ? "Authorization required" : "Waiting for device"
                            font.pixelSize: 11; font.weight: Font.DemiBold
                            color: page.current ? Theme.positive : page.blocked ? Theme.amber : Theme.muted
                        }
                    }
                }
                Type {
                    Layout.fillWidth: true; font.pixelSize: page.compact ? 20 : 25
                    font.weight: Font.DemiBold; font.letterSpacing: -0.45
                    wrapMode: Text.NoWrap; elide: Text.ElideRight
                    text: page.current ? page.current.display_name.split(" · ")[0] : page.blocked ? "Authorize your device" : "Connect your device"
                }
                Type {
                    Layout.fillWidth: true; quiet: true
                    wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                    text: page.current ? page.current.serial + (page.compact ? (page.wireless ? " · Wi-Fi" : " · USB") : "")
                                       : page.blocked ? page.blocked.serial + " · " + page.blocked.state + ". Unlock your phone and allow USB debugging."
                                       : "Enable USB debugging and plug in your phone, or pair over Wi-Fi."
                }
            }
            RowLayout {
                DeckButton { objectName: "scanButton"; text: "Scan devices"; glyph: "refresh"; compact: page.compact; primary: !page.current; enabled: !deck.state.busy; onClicked: deck.scan() }
                DeckButton { visible: !page.current; text: "Setup guide"; compact: page.compact; onClicked: page.window.page = 5 }
                Choice {
                    id: deviceChoice
                    objectName: "deviceChoice"
                    menuLabel: "Active device"
                    menuRowHeight: 52
                    enabled: !deck.state.busy
                    visible: page.ready.length > 1
                    Layout.preferredWidth: Math.min(250, page.compact ? hero.width * 0.31 : hero.width - 148)
                    Layout.preferredHeight: page.compact ? 33 : implicitHeight
                    model: page.ready; textRole: "display_name"; valueRole: "serial"
                    currentIndex: page.ready.findIndex(d => d.serial === deck.state.serial)
                    displayText: page.current ? page.current.display_name + " · " + page.current.serial : ""
                    popup.width: Math.max(width, Math.min(360, page.width - 30))
                    popup.x: width - popup.width
                    delegate: DropdownItem {
                        required property int index; required property var modelData
                        objectName: "deviceChoiceOption" + index
                        width: deviceChoice.popup.availableWidth
                        label: modelData.display_name
                        detail: modelData.serial
                        selected: deviceChoice.currentIndex === index
                        highlighted: deviceChoice.highlightedIndex === index
                    }
                    Accessible.name: "Active device"; onActivated: index => deck.select(page.ready[index].serial)
                }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: page.contentSpacing
        Card {
            enabled: !deck.state.busy
            Layout.fillHeight: true; Layout.preferredWidth: 480
            inset: page.cardInset; spacing: page.cardSpacing
            title: "Wireless connection"; glyph: "wifi"
            RowLayout {
                Layout.fillWidth: true
                Repeater {
                    model: ["USB assisted", "Pair with code"]
                    DeckButton {
                        required property int index; required property string modelData
                        Layout.fillWidth: true; text: modelData; selected: page.window.direct === (index === 1)
                        compact: page.compact
                        onClicked: page.window.direct = index === 1
                    }
                }
            }
            Type {
                Layout.fillWidth: true; quiet: true
                text: page.window.direct ? "Wireless debugging → Pair device with pairing code."
                    : page.current && !page.wireless && deck.state.tcpSerial === deck.state.serial ? "Connect over Wi-Fi, then unplug the USB cable."
                    : "Use a USB connection to enable Wi-Fi mirroring on port 5555."
            }
            RowLayout {
                Layout.fillWidth: true
                Type { text: "Device IP address"; font.bold: true; font.pixelSize: 13 }
                Field { Layout.fillWidth: true; Layout.minimumWidth: 110; Layout.preferredHeight: page.compact ? 33 : implicitHeight; text: deck.settings.ip; placeholderText: "192.168.1.15"; Accessible.name: "Device IP address"; onTextEdited: deck.configure("ip", text) }
                DeckButton { visible: !page.window.direct; text: "Get IP"; compact: page.compact; enabled: !!page.current && !deck.state.busy; onClicked: deck.getIp() }
            }
            RowLayout {
                visible: !page.window.direct; Layout.fillWidth: true
                DeckButton { text: "Enable TCP/IP"; compact: page.compact; enabled: !!page.current && !deck.state.busy; onClicked: deck.enableTcp() }
                DeckButton { text: "Connect Wi-Fi"; compact: page.compact; enabled: !deck.state.busy; onClicked: deck.connectWifi("5555", true) }
            }
            GridLayout {
                visible: page.window.direct; Layout.fillWidth: true; columns: 3; rowSpacing: 3
                Type { text: "Pair port"; font.pixelSize: 13 }
                Type { text: "Pairing code"; Layout.columnSpan: 2; font.pixelSize: 13 }
                Field { Layout.fillWidth: true; Layout.preferredWidth: 80; Layout.preferredHeight: page.compact ? 33 : implicitHeight; placeholderText: "37283"; Accessible.name: "Pair port"; text: page.window.pairPort; onTextEdited: page.window.pairPort = text }
                Field { Layout.fillWidth: true; Layout.preferredWidth: 100; Layout.preferredHeight: page.compact ? 33 : implicitHeight; placeholderText: "6 digits"; Accessible.name: "Pairing code"; maximumLength: 6; echoMode: TextInput.Password; text: page.window.pairCode; onTextEdited: page.window.pairCode = text }
                DeckButton { text: "Pair"; compact: page.compact; enabled: !deck.state.busy; onClicked: deck.pair(page.window.pairPort, page.window.pairCode) }
            }
            RowLayout {
                visible: page.window.direct; Layout.fillWidth: true
                Type { text: "Connection port"; font.pixelSize: 13 }
                Field { Layout.fillWidth: true; Layout.minimumWidth: 62; Layout.preferredHeight: page.compact ? 33 : implicitHeight; placeholderText: "42911"; Accessible.name: "Connection port"; text: deck.state.port; onTextEdited: deck.setPort(text) }
                DeckButton { text: "Detect"; compact: page.compact; enabled: !deck.state.busy; onClicked: deck.detectPort() }
                DeckButton { text: "Connect"; compact: page.compact; enabled: !deck.state.busy; onClicked: deck.connectWifi(deck.state.port) }
            }
        }
        Card {
            title: "Session preview"; glyph: "monitor"; Layout.preferredWidth: 308; Layout.fillHeight: true
            inset: page.cardInset; spacing: page.cardSpacing
            Repeater {
                model: [
                    ["Source", Theme.sourceName(deck.settings.source) + (deck.settings.source === "screen" && deck.settings.screen_mode === "OTG" ? " · OTG" : "")],
                    ["Video", page.otg || page.mic ? "Off" : deck.settings.bitrate + " Mbps · " + (page.fps === "0" ? "Auto" : page.fps) + " fps"],
                    ["Maximum size", page.otg || page.mic ? "—" : page.sizeLimit === "0" ? "Native size" : page.sizeLimit + " px"],
                    ["Audio", page.otg || page.camera || (deck.settings.no_audio && !page.mic) ? "Off" : deck.settings.audio_codec.toUpperCase()],
                    ["Renderer", page.otg || page.mic ? "—" : deck.settings.renderer],
                    ["Window", page.otg ? "Control only" : page.mic ? "Audio only" : deck.settings.fullscreen ? "Fullscreen" : deck.settings.borderless ? "Borderless" : "Windowed"],
                    ["Recording", deck.settings.record && !page.otg ? "MP4 enabled" : "Off"]
                ]
                RowLayout {
                    required property var modelData; Layout.fillWidth: true
                    Type { Layout.fillWidth: true; Layout.preferredWidth: 1; text: modelData[0]; quiet: true; font.pixelSize: 13; wrapMode: Text.NoWrap }
                    Type { Layout.fillWidth: true; Layout.preferredWidth: 1; text: modelData[1]; font.pixelSize: 13; font.bold: true; wrapMode: Text.NoWrap; elide: Text.ElideRight; horizontalAlignment: Text.AlignRight }
                }
            }
            DeckButton { text: "Quick settings"; glyph: "sliders"; compact: true; onClicked: page.window.openQuick() }
        }
    }
}
