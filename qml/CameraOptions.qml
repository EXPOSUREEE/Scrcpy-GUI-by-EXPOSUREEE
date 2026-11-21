import QtQuick
import QtQuick.Layouts

ColumnLayout {
    Layout.fillWidth: true; spacing: 10
    Option { label: "Camera lens"; setting: "camera_id"; options: deck.state.lenses.includes(deck.settings.camera_id) ? deck.state.lenses : deck.state.lenses.concat([deck.settings.camera_id]) }
    DeckButton { Layout.alignment: Qt.AlignRight; compact: true; text: "Detect lenses"; enabled: !deck.state.busy; onClicked: deck.detectLenses() }

    /* Camera torch with runtime capability gating */
    ColumnLayout {
        Layout.fillWidth: true; spacing: 3
        Toggle {
            text: "Enable camera torch"; setting: "camera_torch"
            enabled: !deck.capabilities.camera_torch || deck.capabilities.camera_torch.supported
        }
        RowLayout {
            visible: !!deck.capabilities.camera_torch && !deck.capabilities.camera_torch.supported
            Layout.fillWidth: true; spacing: 8
            Type {
                Layout.fillWidth: true
                text: "Requires scrcpy 4.0+ (active runtime is v" + (deck.state.scrcpyVersion || deck.scrcpy_version) + ")"
                color: Theme.muted; font.pixelSize: 11
            }
            DeckButton {
                compact: true; text: "Update scrcpy"; glyph: "refresh"
                onClicked: deck.openHelpSection("help", "Updates")
            }
        }
    }

    Option { label: "Camera facing"; setting: "source"; options: ["Specific camera lens", "Back camera", "Front camera"]; values: ["camera", "camera_back", "camera_front"] }
    Limiter { label: "Camera bitrate"; setting: "bitrate"; low: 1; high: 64; unit: "Mbps" }
    Limiter { label: "Maximum camera size"; setting: "camera_max_size"; high: 2560; unit: "px"; zero: "Native size" }
    Limiter { label: "Camera frame rate"; setting: "camera_fps"; high: 60; unit: "fps" }
    Option { label: "Aspect ratio"; setting: "cam_ar"; options: ["Full Sensor (Default)", "4:3", "16:9"] }
    Option { label: "Camera rotation"; setting: "cam_orientation"; options: ["0° (Default)", "90°", "180°", "270°"] }

    /* Camera zoom with runtime capability gating */
    ColumnLayout {
        Layout.fillWidth: true; spacing: 3
        RowLayout {
            Layout.fillWidth: true
            Type {
                Layout.fillWidth: true; text: "Camera zoom"
                color: (deck.capabilities.camera_zoom && !deck.capabilities.camera_zoom.supported) ? Theme.muted : Theme.text
            }
            Field {
                Layout.preferredWidth: 95; text: deck.settings.camera_zoom
                enabled: !deck.capabilities.camera_zoom || deck.capabilities.camera_zoom.supported
                Accessible.name: "Camera zoom"
                validator: DoubleValidator { bottom: 0.01; notation: DoubleValidator.StandardNotation; locale: "C" }
                onTextEdited: deck.configure("camera_zoom", text)
            }
        }
        RowLayout {
            visible: !!deck.capabilities.camera_zoom && !deck.capabilities.camera_zoom.supported
            Layout.fillWidth: true; spacing: 8
            Type {
                Layout.fillWidth: true
                text: "Requires scrcpy 4.0+ (active runtime is v" + (deck.state.scrcpyVersion || deck.scrcpy_version) + ")"
                color: Theme.muted; font.pixelSize: 11
            }
            DeckButton {
                compact: true; text: "Update scrcpy"; glyph: "refresh"
                onClicked: deck.openHelpSection("help", "Updates")
            }
        }
    }

    Toggle { text: "Record camera stream to MP4"; setting: "record" }
    Toggle { text: "Always on top"; setting: "always_on_top" }
    Toggle { text: "Fullscreen"; setting: "fullscreen" }
    Toggle { text: "Borderless window"; setting: "borderless" }
}
