import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: row
    property string label
    property string setting
    property string unit
    property string zero: "Auto"
    property int low: 0
    property int high
    spacing: 2
    Layout.fillWidth: true
    RowLayout {
        Layout.fillWidth: true
        Type { text: row.label; Layout.fillWidth: true }
        Type { color: Theme.mint; font.family: Theme.mono; font.pixelSize: 12; text: bar.value > 0 ? Math.round(bar.value) + " " + row.unit : row.zero }
    }
    Slider {
        id: bar
        palette.dark: "#7ec39e"
        palette.window: Theme.mint
        palette.midlight: "#3c4d48"
        palette.mid: "#739585"
        Accessible.name: row.label
        Layout.fillWidth: true
        from: row.low; to: row.high; stepSize: 1
        value: Number(deck.settings[row.setting] || 0)
        onMoved: deck.configure(row.setting, String(Math.round(value)))
    }
}
