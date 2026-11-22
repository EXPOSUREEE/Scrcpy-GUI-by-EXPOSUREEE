import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ScrollView {
    id: sheet
    default property alias contents: items.data
    property int contentSpacing: 14
    property alias columns: items.columns
    contentWidth: availableWidth
    clip: true
    rightPadding: contentHeight > availableHeight ? effectiveScrollBarWidth + 4 : 0
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    GridLayout {
        id: items
        width: sheet.availableWidth
        columns: 1
        rowSpacing: sheet.contentSpacing
        columnSpacing: sheet.contentSpacing
    }
}
