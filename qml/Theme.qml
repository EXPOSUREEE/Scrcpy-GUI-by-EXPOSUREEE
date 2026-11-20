pragma Singleton
import QtQuick
QtObject {
    readonly property color base: "#101618"
    readonly property color rail: "#131b1c"
    readonly property color panel: "#1a2325"
    readonly property color input: "#11191b"
    readonly property color line: "#344143"
    readonly property color text: "#edf4ef"
    readonly property color muted: "#a1b2ad"
    readonly property color mint: "#a5ebc7"
    readonly property color amber: "#f3c880"
    readonly property color danger: "#ffb4a9"
    readonly property string mono: "Cascadia Code"
    readonly property var orientations: ["Auto (Rotate with Phone)", "Portrait (@0)", "Landscape (@90)", "Portrait Reversed (@180)", "Landscape Reversed (@270)"]
    readonly property var sources: ["screen", "camera", "camera_back", "camera_front", "mic_only"]
    readonly property var sourceNames: ["Screen", "Camera", "Back camera", "Front camera", "Microphone"]
    readonly property var inputModes: ["Mirror and control", "Mirror with HID input", "OTG · USB control only"]
    readonly property var inputValues: ["HID", "UHID", "OTG"]
    function sourceName(value) { return sourceNames[sources.indexOf(value)] || value }
}
