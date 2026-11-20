import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Sheet {
    id: page
    property string section: "USB debugging"
    property string brand: "Samsung"
    Flow {
        Layout.fillWidth: true; spacing: 6
        Repeater {
            model: ["USB debugging", "Updates", "Resources", "Videos", "FAQ"]
            DeckButton {
                required property string modelData
                text: modelData
                selected: page.section === text
                onClicked: {
                    page.section = text
                    if (text === "Updates" && !deck.state.scrcpyStatus) {
                        deck.checkScrcpyUpdate()
                    }
                }
            }
        }
    }
    Card {
        visible: page.section === "Updates"; title: "Scrcpy Deck updates"; glyph: "deck"
        Type {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: "Keep the Scrcpy Deck desktop application updated with the latest features, improvements, and bug fixes."
            quiet: true
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 16
            ColumnLayout {
                spacing: 2
                Type { text: "Installed version"; font.pixelSize: 12; quiet: true }
                Type { text: "v" + deck.version; font.weight: Font.DemiBold; font.pixelSize: 15 }
            }
            Rectangle { implicitWidth: 1; implicitHeight: 32; color: Theme.line }
            ColumnLayout {
                spacing: 2
                Type { text: "Latest release"; font.pixelSize: 12; quiet: true }
                Type {
                    text: deck.state.update ? ("v" + deck.state.update + " (Update available)")
                        : (deck.state.updateStatus === "checking" ? "Checking…" : ("v" + deck.version + " (Latest)"))
                    color: deck.state.update ? Theme.accent : Theme.text
                    font.weight: Font.DemiBold; font.pixelSize: 15
                }
            }
        }
        Rectangle {
            visible: deck.state.updateStatus === "downloading"
            Layout.fillWidth: true; implicitHeight: 8; radius: 4; color: Theme.input
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, (deck.state.updateProgress || 0) / 100))
                height: parent.height; radius: 4; color: Theme.accentFill
            }
        }
        Type {
            visible: deck.state.updateStatus === "downloading"
            Layout.fillWidth: true; quiet: true
            text: "Downloading update… " + deck.state.updateProgress + "%"
        }
        Type {
            visible: deck.state.updateStatus === "installing"
            Layout.fillWidth: true; font.bold: true; color: Theme.accent
            text: "Installing update and restarting Scrcpy Deck…"
        }
        Type {
            visible: deck.state.updateStatus === "error"
            Layout.fillWidth: true; color: Theme.danger; wrapMode: Text.Wrap
            text: "Update error: " + deck.state.updateError
        }
        Type {
            visible: !deck.state.update && deck.state.updateStatus !== "checking" && deck.state.updateStatus !== "downloading" && deck.state.updateStatus !== "installing" && deck.state.updateStatus !== "error"
            Layout.fillWidth: true; color: Theme.positive
            text: "✓ Scrcpy Deck is up to date."
        }
        Flow {
            Layout.fillWidth: true; spacing: 8
            DeckButton {
                text: "Check for updates"; glyph: "refresh"
                enabled: deck.state.updateStatus !== "downloading" && deck.state.updateStatus !== "installing"
                onClicked: deck.checkForUpdates()
            }
            DeckButton {
                visible: !!deck.state.update
                primary: true; text: "Install update v" + deck.state.update; glyph: "download"
                enabled: deck.state.updateStatus !== "downloading" && deck.state.updateStatus !== "installing"
                onClicked: deck.installUpdate()
            }
            DeckButton {
                text: "Releases on GitHub"; glyph: "globe"
                onClicked: Qt.openUrlExternally("https://github.com/EXPOSUREEE/ScrcpyDeck-Desktop/releases")
            }
        }
    }
    Card {
        visible: page.section === "Updates"; title: "Scrcpy core engine updates"; glyph: "tools"
        Type {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: "Scrcpy is the open-source screen and camera mirroring engine by Genymobile. Check for and install the latest scrcpy binary distribution directly into your local runtime."
            quiet: true
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 16
            ColumnLayout {
                spacing: 2
                Type { text: "Installed runtime"; font.pixelSize: 12; quiet: true }
                Type { text: deck.state.scrcpyVersion ? ("v" + deck.state.scrcpyVersion) : ("v" + deck.scrcpy_version); font.weight: Font.DemiBold; font.pixelSize: 15 }
            }
            Rectangle { implicitWidth: 1; implicitHeight: 32; color: Theme.line }
            ColumnLayout {
                spacing: 2
                Type { text: "Latest on GitHub"; font.pixelSize: 12; quiet: true }
                Type {
                    text: deck.state.scrcpyLatest ? ("v" + deck.state.scrcpyLatest + (deck.state.scrcpyStatus === "available" ? " (Update available)" : " (Up to date)"))
                        : (deck.state.scrcpyStatus === "checking" ? "Checking…" : "Not checked")
                    color: deck.state.scrcpyStatus === "available" ? Theme.accent : Theme.text
                    font.weight: Font.DemiBold; font.pixelSize: 15
                }
            }
        }
        Rectangle {
            visible: deck.state.scrcpyStatus === "downloading"
            Layout.fillWidth: true; implicitHeight: 8; radius: 4; color: Theme.input
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, (deck.state.scrcpyProgress || 0) / 100))
                height: parent.height; radius: 4; color: Theme.accentFill
            }
        }
        Type {
            visible: deck.state.scrcpyStatus === "downloading"
            Layout.fillWidth: true; quiet: true
            text: "Downloading scrcpy core binaries… " + deck.state.scrcpyProgress + "%"
        }
        Type {
            visible: deck.state.scrcpyStatus === "installing"
            Layout.fillWidth: true; font.bold: true; color: Theme.accent
            text: "Extracting binaries into runtime directory…"
        }
        Type {
            visible: deck.state.scrcpyStatus === "installed"
            Layout.fillWidth: true; color: Theme.positive; font.bold: true
            text: "✓ Scrcpy runtime updated successfully to v" + deck.state.scrcpyVersion + "!"
        }
        Type {
            visible: deck.state.scrcpyStatus === "up-to-date"
            Layout.fillWidth: true; color: Theme.positive
            text: "✓ Scrcpy runtime is up to date."
        }
        Type {
            visible: deck.state.scrcpyStatus === "error"
            Layout.fillWidth: true; color: Theme.danger; wrapMode: Text.Wrap
            text: "Scrcpy update error: " + deck.state.scrcpyError
        }
        Flow {
            Layout.fillWidth: true; spacing: 8
            DeckButton {
                text: "Check scrcpy update"; glyph: "refresh"
                enabled: deck.state.scrcpyStatus !== "downloading" && deck.state.scrcpyStatus !== "installing"
                onClicked: deck.checkScrcpyUpdate()
            }
            DeckButton {
                visible: deck.state.scrcpyStatus === "available"
                primary: true; text: "Install scrcpy v" + deck.state.scrcpyLatest; glyph: "download"
                enabled: deck.state.scrcpyStatus !== "downloading" && deck.state.scrcpyStatus !== "installing"
                onClicked: deck.installScrcpyUpdate()
            }
            DeckButton {
                text: "Genymobile scrcpy repo"; glyph: "globe"
                onClicked: Qt.openUrlExternally("https://github.com/Genymobile/scrcpy/releases")
            }
        }
    }
    Card {
        visible: page.section === "USB debugging"; title: "Enable USB debugging"; glyph: "phone"
        Choice { objectName: "brandChoice"; Accessible.name: "Phone manufacturer"; menuLabel: "Phone manufacturer"; Layout.fillWidth: true; model: Object.keys(deck.guides.steps); currentIndex: model.indexOf(page.brand); onActivated: index => page.brand = model[index] }
        Repeater {
            model: deck.guides.steps[page.brand]
            Type { required property string modelData; required property int index; Layout.fillWidth: true; text: (index + 1) + ".  " + modelData }
        }
        DeckButton { text: "Find a video for " + page.brand; onClicked: Qt.openUrlExternally("https://www.youtube.com/results?search_query=" + encodeURIComponent("how to enable usb debugging " + page.brand)) }
    }
    Card {
        visible: page.section === "Resources"; title: "Project resources"; glyph: "globe"
        DeckButton { text: "Project & downloads"; onClicked: Qt.openUrlExternally("https://exposureee.in/scrcpy-gui-by-exposureee/") }
        DeckButton { text: "Creator on GitHub"; onClicked: Qt.openUrlExternally("https://github.com/EXPOSUREEE") }
        DeckButton { text: "Watch setup tutorial"; onClicked: Qt.openUrlExternally("https://www.youtube.com/watch?v=pWKY_dntX5c") }
        DeckButton { text: "Support the creator"; onClicked: donation.open() }
    }
    Card {
        visible: page.section === "Videos"; title: "Creator tutorials"; glyph: "video"
        Repeater {
            model: deck.guides.videos
            ItemDelegate {
                required property var modelData; Layout.fillWidth: true; implicitHeight: contentItem.implicitHeight + 18
                contentItem: Type { text: parent.modelData[0]; color: Theme.accent }
                onClicked: Qt.openUrlExternally(modelData[1])
            }
        }
    }
    Card {
        visible: page.section === "FAQ"; title: "Frequently asked questions"; glyph: "help"
        Repeater {
            model: deck.guides.faqs
            ColumnLayout {
                required property var modelData; Layout.fillWidth: true; spacing: 4
                Type { Layout.fillWidth: true; text: modelData[0].replace(/^Q: /, ""); font.bold: true }
                Type { Layout.fillWidth: true; text: modelData[1].replace(/^A: /, ""); quiet: true }
            }
        }
    }
    DeckDialog {
        id: donation; title: "Support EXPOSUREEE"; standardButtons: Dialog.Close
        ColumnLayout {
            width: parent.width
            Type { text: "Abhishek Mishra"; font.bold: true }
            Type { text: "exposureee@upi"; font.family: Theme.mono }
            DeckButton { text: "Copy UPI ID"; onClicked: deck.copy("exposureee@upi") }
            DeckButton { text: "Open payment QR"; onClicked: Qt.openUrlExternally("https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + encodeURIComponent("upi://pay?pa=exposureee@upi&pn=Abhishek%20Mishra&cu=INR")) }
        }
    }
}
