import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
DeckDialog {
    id: edit; title: "Edit saved device"
    property int deviceIndex: -1
    readonly property var record: deck.saved[deviceIndex] || ({})
    onOpened: { nickname.text = record.nickname || ""; ip.text = record.ip || ""; nickname.forceActiveFocus() }
    ColumnLayout {
        width: parent.width; spacing: 10
        Type { text: "Nickname" }
        Field { id: nickname; Layout.fillWidth: true; placeholderText: "Primary phone"; Accessible.name: "Nickname" }
        Type { visible: edit.record.type === "wireless"; text: "Wi-Fi IP address" }
        Field { id: ip; visible: edit.record.type === "wireless"; Layout.fillWidth: true; Accessible.name: "Wi-Fi IP address" }
        Type { visible: !!deck.state.error; Layout.fillWidth: true; color: Theme.danger; text: deck.state.error }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            DeckButton { text: "Cancel"; onClicked: edit.close() }
            DeckButton { primary: true; text: "Save changes"; onClicked: { if (deck.editSaved(edit.deviceIndex, nickname.text, ip.text)) edit.close() } }
        }
    }
}
