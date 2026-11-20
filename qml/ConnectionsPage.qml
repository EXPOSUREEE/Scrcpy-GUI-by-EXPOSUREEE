import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Sheet {
    id: page
    readonly property var window: ApplicationWindow.window
    readonly property var ready: deck.state.devices.filter(d => d.state === "device")
    readonly property var current: ready.find(d => d.serial === deck.state.serial)
    readonly property bool wireless: current ? current.transport === "wireless" : false
    readonly property var blocked: deck.state.devices.find(d => d.state !== "device")
    readonly property bool wide: availableWidth >= 840
    readonly property bool otg: deck.settings.source === "screen" && deck.settings.screen_mode === "OTG"
    readonly property bool camera: deck.settings.source.startsWith("camera")
    readonly property bool mic: deck.settings.source === "mic_only"
    readonly property string fps: (camera ? deck.settings.camera_fps : deck.settings.max_fps) || "0"
    readonly property string sizeLimit: (camera ? deck.settings.camera_max_size : deck.settings.max_size) || "0"
    Rectangle {
        Layout.fillWidth: true; implicitHeight: Math.max(172, hero.implicitHeight + 36)
        radius: 15; clip: true; border.color: "#4a665b"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "#243c32" }
            GradientStop { position: 0.63; color: "#213a33" }
            GradientStop { position: 1; color: "#1a302e" }
        }
        SignalArt { width: parent.width > 570 ? Math.min(parent.width*0.31, 300) : 0; height: parent.height - 4; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; visible: width > 0 }
        ColumnLayout {
            id: hero; x: 22; anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.67 - 30; spacing: 6
            RowLayout {
                spacing: 8
                Rectangle { width: 7; height: 7; radius: 4; color: page.current ? Theme.mint : Theme.amber }
                Type { text: page.current ? (page.wireless ? "WIRELESS LINK" : "DEVICE LINK") : "DEVICE DISCOVERY"; color: "#c6dfcf"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.5 }
            }
            Type { Layout.fillWidth: true; text: page.current ? page.current.display_name.split(" · ")[0] : page.blocked ? "Authorize your device" : "Connect your device"; font.pixelSize: 29; font.bold: true }
            Type {
                Layout.fillWidth: true; color: "#c2d4c8"
                text: page.current ? page.current.serial : page.blocked ? page.blocked.serial + " · " + page.blocked.state + ". Unlock your phone and check USB debugging." : "Plug in your phone and allow USB debugging, or pair over Wi-Fi below."
            }
            RowLayout {
                Layout.topMargin: 5
                DeckButton { objectName: "scanButton"; text: "Scan devices"; glyph: "\ue72c"; primary: true; enabled: !deck.state.busy; onClicked: deck.scan() }
                DeckButton { visible: !page.current; text: "Setup guide"; onClicked: page.window.page = 5 }
                Choice {
                    enabled: !deck.state.busy
                    visible: page.ready.length > 1; Layout.preferredWidth: Math.min(250, hero.width - 148)
                    model: page.ready; textRole: "display_name"; valueRole: "serial"
                    currentIndex: page.ready.findIndex(d => d.serial === deck.state.serial)
                    displayText: page.current ? page.current.display_name + " · " + page.current.serial : ""
                    delegate: ItemDelegate { required property var modelData; width: parent ? parent.width : 200; text: modelData.display_name + " · " + modelData.serial }
                    Accessible.name: "Active device"; onActivated: index => deck.select(page.ready[index].serial)
                }
            }
        }
    }
    GridLayout {
        Layout.fillWidth: true; columns: page.wide ? 2 : 1; rowSpacing: 14; columnSpacing: 14
        Card {
            enabled: !deck.state.busy
            Layout.alignment: Qt.AlignTop; Layout.preferredWidth: 480
            title: "Wireless connection"; glyph: "\ue701"
            RowLayout {
                Layout.fillWidth: true
                Repeater {
                    model: ["USB assisted", "Pair with code"]
                    DeckButton {
                        required property int index; required property string modelData
                        Layout.fillWidth: true; text: modelData; primary: page.window.direct === (index === 1)
                        onClicked: page.window.direct = index === 1
                    }
                }
            }
            Type { Layout.fillWidth: true; quiet: true; text: page.window.direct ? "On Android 11+, open Wireless debugging and choose Pair device with pairing code." : "Use a USB connection to enable Wi-Fi mirroring on port 5555." }
            Type { text: "Device IP address"; font.bold: true; font.pixelSize: 13 }
            RowLayout {
                Layout.fillWidth: true
                Field { Layout.fillWidth: true; text: deck.settings.ip; placeholderText: "192.168.1.15"; Accessible.name: "Device IP address"; onTextEdited: deck.configure("ip", text) }
                DeckButton { visible: !page.window.direct; text: "Get IP"; enabled: !!page.current && !deck.state.busy; onClicked: deck.getIp() }
            }
            RowLayout {
                visible: !page.window.direct; Layout.fillWidth: true
                DeckButton { text: "Enable TCP/IP"; enabled: !!page.current && !deck.state.busy; onClicked: deck.enableTcp() }
                DeckButton { text: "Connect Wi-Fi"; enabled: !deck.state.busy; onClicked: deck.connectWifi("5555", true) }
            }
            GridLayout {
                visible: page.window.direct; Layout.fillWidth: true; columns: 3
                Type { text: "Pair port"; font.pixelSize: 13 }
                Type { text: "Pairing code"; Layout.columnSpan: 2; font.pixelSize: 13 }
                Field { Layout.fillWidth: true; Layout.preferredWidth: 80; placeholderText: "37283"; Accessible.name: "Pair port"; text: page.window.pairPort; onTextEdited: page.window.pairPort = text }
                Field { Layout.fillWidth: true; Layout.preferredWidth: 100; placeholderText: "6 digits"; Accessible.name: "Pairing code"; maximumLength: 6; echoMode: TextInput.Password; text: page.window.pairCode; onTextEdited: page.window.pairCode = text }
                DeckButton { text: "Pair"; enabled: !deck.state.busy; onClicked: deck.pair(page.window.pairPort, page.window.pairCode) }
                Type { text: "Connection port"; Layout.columnSpan: 3; font.pixelSize: 13 }
                Field { Layout.fillWidth: true; placeholderText: "42911"; Accessible.name: "Connection port"; text: deck.state.port; onTextEdited: deck.setPort(text) }
                DeckButton { text: "Detect"; enabled: !deck.state.busy; onClicked: deck.detectPort() }
                DeckButton { text: "Connect"; enabled: !deck.state.busy; onClicked: deck.connectWifi(deck.state.port) }
            }
        }
        Card {
            title: "Session preview"; glyph: "\ue7f4"; Layout.preferredWidth: 308; Layout.alignment: Qt.AlignTop
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
                    Type { Layout.fillWidth: true; text: modelData[0]; quiet: true; font.pixelSize: 13 }
                    Type { text: modelData[1]; font.pixelSize: 13; font.bold: true }
                }
            }
            DeckButton { text: "Quick settings"; glyph: "\ue9e9"; compact: true; onClicked: page.window.openQuick() }
        }
    }
    Card {
        title: "Next step"; glyph: "\ue946"
        visible: !!page.current || !!deck.state.error
        Type {
            Layout.fillWidth: true; quiet: true
            text: deck.state.error ? deck.state.error : page.wireless ? "Your wireless link is ready. Start a session when you’re ready to mirror."
                : !page.current ? "Enable Developer options and USB debugging, connect a data cable and scan for devices."
                : !deck.settings.ip ? "Mirror over USB now, or read the phone’s Wi-Fi address to continue wirelessly."
                : deck.state.tcpSerial !== deck.state.serial ? "Enable TCP/IP for the selected device to continue over Wi-Fi." : "Connect to the phone over Wi-Fi, then unplug the cable."
        }
        RowLayout {
            DeckButton {
                text: deck.state.error ? "Open console" : page.wireless || (page.current && !deck.settings.ip) ? "Start mirroring" : !page.current ? "Scan devices" : deck.state.tcpSerial === deck.state.serial ? "Connect Wi-Fi" : "Enable TCP/IP"
                enabled: !deck.state.busy
                onClicked: {
                    if (deck.state.error) page.window.page = 4
                    else if (!page.current) deck.scan()
                    else if (page.wireless || !deck.settings.ip) deck.launch()
                    else if (deck.state.tcpSerial === deck.state.serial) deck.connectWifi("5555", true)
                    else deck.enableTcp()
                }
            }
            DeckButton { visible: !!page.current && !page.wireless && !deck.settings.ip; text: "Get Wi-Fi address"; enabled: !deck.state.busy; onClicked: deck.getIp() }
        }
    }
    Card {
        title: "ADB utilities"; glyph: "\ue90f"
        RowLayout {
            DeckButton { text: "Stop ADB server"; enabled: !deck.state.busy; onClicked: page.window.askMaintenance("stop") }
            DeckButton { text: "Reset connections"; enabled: !deck.state.busy; onClicked: page.window.askMaintenance("reset") }
        }
    }
}
