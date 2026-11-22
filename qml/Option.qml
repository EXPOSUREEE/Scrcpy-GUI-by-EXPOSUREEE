import QtQuick
import QtQuick.Layouts
RowLayout {
    id: row
    property string label
    property string setting
    property var options: []
    property var values: options
    Layout.fillWidth: true
    Type { text: row.label; Layout.fillWidth: true }
    Choice {
        objectName: row.setting + "Choice"
        Layout.preferredWidth: 228
        menuLabel: row.label
        model: row.options
        currentIndex: row.values.indexOf(deck.settings[row.setting])
        onActivated: index => deck.configure(row.setting, row.values[index])
        Accessible.name: row.label
    }
}
