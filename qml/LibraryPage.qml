import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Sheet {
    id: page
    readonly property var window: ApplicationWindow.window
    Card {
        visible: !deck.saved.length; title: "Your device library"; glyph: "\ue8f1"
        Type { Layout.fillWidth: true; quiet: true; text: "Devices appear here after an authorized USB or wireless connection. Give a device a nickname or reconnect to start its next session." }
        DeckButton { text: "Find devices"; onClicked: { page.window.page = 0; deck.scan() } }
    }
    Repeater {
        model: deck.saved
        Card {
            required property var modelData; required property int index
            title: modelData.nickname || modelData.display_name || modelData.model || "Android device"
            glyph: modelData.type === "wireless" ? "\ue701" : "\ue88e"
            Type { Layout.fillWidth: true; quiet: true; text: [modelData.nickname ? modelData.display_name : "", modelData.serial || modelData.ip].filter(Boolean).join("   ·   "); font.family: Theme.mono; font.pixelSize: 12 }
            RowLayout {
                enabled: !deck.state.busy
                DeckButton { primary: true; text: "Connect & start"; onClicked: deck.connectSaved(index) }
                DeckButton { text: "Edit"; onClicked: page.window.openEditor(index) }
                DeckButton { text: "Forget"; onClicked: page.window.askForget(index) }
            }
        }
    }
}
