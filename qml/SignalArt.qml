import QtQuick

Rectangle {
    id: art
    property bool connected: false
    property bool wireless: false
    readonly property color signalColor: connected ? Theme.positive : Theme.accent
    radius: 12
    color: connected ? Theme.positiveSoft : Theme.accentSoft
    Accessible.ignored: true

    Item {
        width: 212
        height: 102
        anchors.centerIn: parent
        scale: Math.min(1, (art.width - 22) / width)

        Rectangle {
            x: 4; y: 15; width: 43; height: 72; radius: 11
            color: Theme.panel
            border.color: art.signalColor
            Rectangle { x: 8; y: 11; width: 27; height: 43; radius: 5; color: art.color }
            Rectangle { x: 16; y: 61; width: 11; height: 2; radius: 1; color: art.signalColor }
        }
        Repeater {
            model: 8
            Rectangle {
                required property int index
                x: 47 + index * 8; y: 50
                width: 4; height: 2; radius: 1
                color: art.signalColor
                opacity: art.connected ? 0.85 : 0.4
            }
        }
        Rectangle {
            x: 62; y: 36; width: 30; height: 30; radius: 15
            color: Theme.panel
            border.color: art.signalColor
            Glyph { anchors.centerIn: parent; name: art.wireless ? "wifi" : "link"; size: 15; color: art.signalColor }
        }
        Rectangle {
            x: 105; y: 19; width: 103; height: 63; radius: 9
            color: Theme.panel
            border.color: art.signalColor
            Rectangle { x: 8; y: 8; width: 87; height: 47; radius: 4; color: art.color }
            Glyph { anchors.centerIn: parent; name: art.connected ? "play" : "phone"; size: 21; color: art.signalColor }
            Rectangle { x: 50; y: 63; width: 2; height: 8; color: art.signalColor }
            Rectangle { x: 39; y: 71; width: 24; height: 2; radius: 1; color: art.signalColor }
        }
    }
}
