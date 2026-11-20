pragma Singleton
import QtQuick
QtObject {
    readonly property bool dark: deck.settings.appearance === "dark"
    readonly property color base: dark ? "#171619" : "#f5f4f5"
    readonly property color rail: dark ? "#1c1b1f" : "#ffffff"
    readonly property color panel: dark ? "#222126" : "#ffffff"
    readonly property color input: dark ? "#1c1b20" : "#f8f7f8"
    readonly property color line: dark ? "#343138" : "#e9e6ea"
    readonly property color controlLine: dark ? "#4c4651" : "#d8d3da"
    readonly property color hover: dark ? "#2e2a32" : "#f1eff2"
    readonly property color pressed: dark ? "#3a3440" : "#e9e5ea"
    readonly property color text: dark ? "#f9f5f8" : "#211d24"
    readonly property color muted: dark ? "#b8b0bc" : "#625c68"
    readonly property color accent: dark ? "#ff93b0" : "#b22651"
    readonly property color accentFill: dark ? "#e14b76" : "#c8325e"
    readonly property color accentHover: dark ? "#ef6089" : "#b62a54"
    readonly property color accentPressed: dark ? "#f27699" : "#9e2047"
    readonly property color accentText: dark ? "#210911" : "#ffffff"
    readonly property color accentSoft: dark ? "#3b2530" : "#fceaf0"
    readonly property color positive: dark ? "#79d5ad" : "#21694f"
    readonly property color positiveSoft: dark ? "#22382f" : "#e8f5ee"
    readonly property color amber: dark ? "#f1c283" : "#8b4a16"
    readonly property color amberSoft: dark ? "#3d3024" : "#fff0dc"
    readonly property color danger: dark ? "#ffadb3" : "#a42039"
    readonly property color dangerSoft: dark ? "#42262d" : "#fdecef"
    readonly property color overlay: dark ? "#aa100e13" : "#661f1922"
    readonly property string sans: "Inter"
    readonly property string mono: "Cascadia Code"
    readonly property var orientations: ["Auto (Rotate with Phone)", "Portrait (@0)", "Landscape (@90)", "Portrait Reversed (@180)", "Landscape Reversed (@270)"]
    readonly property var sources: ["screen", "camera", "camera_back", "camera_front", "mic_only"]
    readonly property var sourceNames: ["Screen", "Camera", "Back camera", "Front camera", "Microphone"]
    readonly property var inputModes: ["Mirror and control", "Mirror with HID input", "OTG · USB control only"]
    readonly property var inputValues: ["HID", "UHID", "OTG"]
    function sourceName(value) { return sourceNames[sources.indexOf(value)] || value }
}
