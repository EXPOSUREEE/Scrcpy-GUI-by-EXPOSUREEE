import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ScrollView {
    id: sheet
    default property alias contents: items.data
    contentWidth: availableWidth
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        id: items
        width: sheet.availableWidth - 12
        spacing: 14
    }
}
