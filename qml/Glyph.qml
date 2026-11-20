import QtQuick
import QtQuick.Shapes

Item {
    id: icon
    property string name: ""
    property color color: Theme.accent
    property int size: 18
    implicitWidth: size
    implicitHeight: size
    Accessible.ignored: true

    readonly property var paths: ({
        deck: "M4 5H20V16H4Z M8 20H16 M12 16V20 M9 12L12 9L15 12",
        link: "M10 13L14 9 M8 16L6.5 17.5A3.5 3.5 0 0 1 1.6 12.6L6 8.2A3.5 3.5 0 0 1 11 8.2 M16 8L17.5 6.5A3.5 3.5 0 0 1 22.4 11.4L18 15.8A3.5 3.5 0 0 1 13 15.8",
        devices: "M3 6A2 2 0 0 1 5 4H13A2 2 0 0 1 15 6V18A2 2 0 0 1 13 20H5A2 2 0 0 1 3 18Z M8 16H10 M18 7H20A1 1 0 0 1 21 8V16A1 1 0 0 1 20 17H18",
        monitor: "M3 5H21V17H3Z M8 21H16 M12 17V21",
        sliders: "M4 6H9 M13 6H20 M4 12H13 M17 12H20 M4 18H7 M11 18H20 M9 4H13V8H9Z M13 10H17V14H13Z M7 16H11V20H7Z",
        terminal: "M3 5H21V19H3Z M7 9L10 12L7 15 M13 15H17",
        help: "M21 12A9 9 0 1 1 3 12A9 9 0 0 1 21 12Z M9.5 9A2.5 2.5 0 1 1 13.5 11C12.5 11.6 12 12.1 12 13 M12 16.5V16.6",
        sun: "M16 12A4 4 0 1 1 8 12A4 4 0 0 1 16 12Z M12 2V4 M12 20V22 M2 12H4 M20 12H22 M5 5L6.5 6.5 M17.5 17.5L19 19 M19 5L17.5 6.5 M6.5 17.5L5 19",
        moon: "M20.5 14.5A9 9 0 0 1 9.5 3.5A9 9 0 1 0 20.5 14.5Z",
        play: "M8 4.8C7.1 4.3 6 4.9 6 5.9V18.1C6 19.1 7.1 19.7 8 19.2L18.5 13.1C19.3 12.6 19.3 11.4 18.5 10.9Z",
        refresh: "M20 10A8 8 0 0 0 6 6L3 9 M3 4V9H8 M4 14A8 8 0 0 0 18 18L21 15 M16 15H21V20",
        wifi: "M3 9A14 14 0 0 1 21 9 M6 12A9.5 9.5 0 0 1 18 12 M9 15A4.8 4.8 0 0 1 15 15 M12 19V19.1",
        tools: "M14 6L17 9L21 5A6 6 0 0 1 13.5 13L6.2 20.3A1.8 1.8 0 0 1 3.7 17.8L11 10.5A6 6 0 0 1 19 3Z",
        phone: "M6 4A2 2 0 0 1 8 2H16A2 2 0 0 1 18 4V20A2 2 0 0 1 16 22H8A2 2 0 0 1 6 20Z M10 18H14",
        chevron: "M6 9L12 15L18 9",
        arrow: "M4 12H20 M14 6L20 12L14 18",
        download: "M12 3V15 M7 10L12 15L17 10 M4 16V21H20V16",
        video: "M3 6H15V18H3Z M15 10L21 7V17L15 14",
        camera: "M3 7H7L9 4H15L17 7H21V20H3Z M15 13A3 3 0 1 1 9 13A3 3 0 0 1 15 13Z",
        window: "M3 4H21V20H3Z M3 9H21 M6 6.5H6.1 M9 6.5H9.1",
        hand: "M8 12V5A1.5 1.5 0 0 1 11 5V10V3.5A1.5 1.5 0 0 1 14 3.5V10V5A1.5 1.5 0 0 1 17 5V11V8A1.5 1.5 0 0 1 20 8V15A6 6 0 0 1 14 21H12A5 5 0 0 1 8 19L4 14A1.8 1.8 0 0 1 6.8 11.8L8 13",
        record: "M21 12A9 9 0 1 1 3 12A9 9 0 0 1 21 12Z M15 12A3 3 0 1 1 9 12A3 3 0 0 1 15 12Z",
        audio: "M3 9H7L12 5V19L7 15H3Z M16 9A4.5 4.5 0 0 1 16 15 M19 6A8.5 8.5 0 0 1 19 18",
        chip: "M6 6H18V18H6Z M10 10H14V14H10Z M9 3V6 M15 3V6 M9 18V21 M15 18V21 M3 9H6 M3 15H6 M18 9H21 M18 15H21",
        globe: "M21 12A9 9 0 1 1 3 12A9 9 0 0 1 21 12Z M3 12H21 M12 3C7 7 7 17 12 21C17 17 17 7 12 3Z",
        copy: "M8 8H20V21H8Z M4 16V3H16",
        trash: "M4 6H20 M9 6V3H15V6 M6 6L7 21H17L18 6 M10 10V17 M14 10V17",
        check: "M5 12L10 17L19 7",
        circle: "M20 12A8 8 0 1 1 4 12A8 8 0 0 1 20 12Z",
        switch: "M16 4L20 8L16 12 M20 8H4 M8 20L4 16L8 12 M4 16H20"
    })

    Shape {
        width: 24
        height: 24
        anchors.centerIn: parent
        scale: icon.size / 24
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: icon.color
            strokeWidth: 1.75
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg { path: icon.paths[icon.name] || "" }
        }
    }
}
