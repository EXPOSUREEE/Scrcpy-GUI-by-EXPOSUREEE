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
        Type { color: Theme.accent; font.pixelSize: 12; font.weight: Font.DemiBold; text: bar.value > 0 ? Math.round(bar.value) + " " + row.unit : row.zero }
    }
    Slider {
        id: bar
        Accessible.name: row.label
        Layout.fillWidth: true
        from: row.low; to: row.high; stepSize: 1
        value: Number(deck.settings[row.setting] || 0)
        onMoved: deck.configure(row.setting, String(Math.round(value)))
        background: Rectangle {
            x: bar.leftPadding + bar.handle.width / 2
            y: bar.topPadding + (bar.availableHeight - height) / 2
            width: bar.availableWidth - bar.handle.width
            height: 4
            radius: 2
            color: Theme.pressed
            Rectangle { width: bar.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.accentFill }
        }
        handle: Rectangle {
            x: bar.leftPadding + bar.visualPosition * (bar.availableWidth - width)
            y: bar.topPadding + (bar.availableHeight - height) / 2
            implicitWidth: 16
            implicitHeight: 16
            radius: 8
            color: Theme.panel
            border.width: bar.visualFocus || bar.pressed ? 3 : 2
            border.color: Theme.accent
        }
    }
}
