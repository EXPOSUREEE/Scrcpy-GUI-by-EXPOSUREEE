import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
DeckDialog {
    id: dialog
    title: "Quick settings"
    width: Math.min(540, parent.width - 36)
    height: Math.min(610, parent.height - 40)
    property int mode: 0
    onOpened: mode = deck.settings.source.startsWith("camera") ? 1 : deck.settings.source === "mic_only" ? 2 : 0
    ColumnLayout {
        anchors.fill: parent; spacing: 14
        RowLayout {
            Layout.fillWidth: true
            Repeater {
                model: ["Screen", "Camera", "Mic"]
                DeckButton {
                    required property int index; required property string modelData
                    Layout.fillWidth: true; text: modelData; selected: dialog.mode === index
                    onClicked: dialog.mode = index
                }
            }
        }
        Sheet {
            Layout.fillWidth: true; Layout.fillHeight: true
            Option { visible: dialog.mode === 0; label: "Connection"; setting: "screen_mode"; options: Theme.inputModes; values: Theme.inputValues }
            ScreenOptions { visible: dialog.mode === 0 }
            Option { visible: dialog.mode === 0; label: "Orientation"; setting: "orientation"; options: Theme.orientations }
            CameraOptions { visible: dialog.mode === 1 }
            AudioOptions { visible: dialog.mode === 2 }
            Type { visible: dialog.mode === 2; Layout.fillWidth: true; quiet: true; text: "Microphone mode forwards the phone’s microphone without video." }
        }
        Type { visible: !!deck.state.error; text: deck.state.error; color: Theme.danger; maximumLineCount: 2; elide: Text.ElideRight; Layout.fillWidth: true }
        DeckButton {
            Layout.alignment: Qt.AlignRight; primary: true; text: "Apply & close"
            onClicked: {
                deck.configure("source", dialog.mode === 0 ? "screen" : dialog.mode === 2 ? "mic_only" : (deck.settings.source.startsWith("camera") ? deck.settings.source : "camera"))
                dialog.close()
            }
        }
    }
}
