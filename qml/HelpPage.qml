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
                    if (text === "Updates"
                            && ((!deck.state.deckReleases || deck.state.deckReleases.length === 0)
                                || (!deck.state.scrcpyReleases || deck.state.scrcpyReleases.length === 0))) {
                        deck.checkAllUpdates(false)
                    }
                }
            }
        }
    }

    /* ── SECTION A: SCRCPY DECK APPLICATION ── */
    Card {
        visible: page.section === "Updates"; title: "Scrcpy Deck updates"; glyph: "deck"
        Type {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: "Manage Scrcpy Deck application versions. Upgrade to newer releases, downgrade to previous releases, or reinstall your current version."
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
                Type { text: "Latest stable"; font.pixelSize: 12; quiet: true }
                Type {
                    text: deck.state.updateStatus === "checking" ? "Checking…"
                        : deck.state.updateStatus === "error" ? "Check failed"
                        : deck.state.deckLatest ? ("v" + deck.state.deckLatest
                            + (deck.state.updateStatus === "offline" ? " (Cached — offline)"
                               : deck.state.update ? " (Update available)" : " (Up to date)"))
                        : "Not checked"
                    color: deck.state.update ? Theme.accent : Theme.text
                    font.weight: Font.DemiBold; font.pixelSize: 15
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; spacing: 4
            Type { text: "Select application version"; font.pixelSize: 12; quiet: true }
            Choice {
                objectName: "deckReleaseChoice"
                Layout.fillWidth: true
                model: deck.state.deckReleaseLabels
                currentIndex: deck.state.selectedDeckIndex || 0
                onActivated: index => deck.selectDeckRelease(index)
            }
        }

        ColumnLayout {
            visible: !!deck.state.selectedDeckInfo && !!deck.state.selectedDeckInfo.version
            Layout.fillWidth: true; spacing: 4
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Type { text: "Selected: v" + (deck.state.selectedDeckInfo.version || ""); font.weight: Font.DemiBold }
                Type { text: "•"; quiet: true; visible: !!deck.state.selectedDeckInfo.date }
                Type { text: "Release date: " + (deck.state.selectedDeckInfo.date || "Unknown"); quiet: true; visible: !!deck.state.selectedDeckInfo.date }
                Type { text: "•"; quiet: true; visible: !!deck.state.selectedDeckInfo.size_str }
                Type { text: "Size: " + (deck.state.selectedDeckInfo.size_str || ""); quiet: true; visible: !!deck.state.selectedDeckInfo.size_str }
                Type { text: "•"; quiet: true; visible: !!deck.state.selectedDeckInfo.action }
                Type {
                    text: "Action: " + (deck.state.selectedDeckInfo.action === "upgrade" ? "Upgrade" : deck.state.selectedDeckInfo.action === "downgrade" ? "Downgrade" : deck.state.selectedDeckInfo.action === "reinstall" ? "Reinstall" : "Install")
                    color: deck.state.selectedDeckInfo.action === "downgrade" ? Theme.amber : Theme.accent
                    font.weight: Font.Medium
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
            visible: deck.state.updateStatus === "up-to-date"
            Layout.fillWidth: true; color: Theme.positive
            text: "✓ Scrcpy Deck is up to date."
        }
        Type {
            visible: deck.state.updateStatus === "offline"
            Layout.fillWidth: true; color: Theme.amber; wrapMode: Text.Wrap
            text: "Offline — showing the most recently cached Scrcpy Deck releases."
        }

        Flow {
            Layout.fillWidth: true; spacing: 8
            DeckButton {
                primary: true
                text: deck.state.deckActionText || "Install"
                glyph: "download"
                enabled: deck.state.updateStatus !== "downloading" && deck.state.updateStatus !== "installing"
                    && !!deck.state.selectedDeckInfo && !!deck.state.selectedDeckInfo.is_compatible
                onClicked: {
                    if (deck.state.selectedDeckInfo && deck.state.selectedDeckInfo.action === "downgrade") {
                        downgradeDialog.open()
                    } else {
                        deck.installSelectedDeck()
                    }
                }
            }
            DeckButton {
                text: "View release notes"; glyph: "globe"
                visible: !!deck.state.selectedDeckInfo && !!deck.state.selectedDeckInfo.html_url
                onClicked: Qt.openUrlExternally(deck.state.selectedDeckInfo.html_url)
            }
            DeckButton {
                text: "Check for updates"; glyph: "refresh"
                enabled: deck.state.updateStatus !== "downloading" && deck.state.updateStatus !== "installing"
                onClicked: deck.checkAllUpdates(true)
            }
            DeckButton {
                visible: deck.state.updateStatus === "downloading"
                text: "Cancel"; glyph: "cancel"
                onClicked: deck.cancelUpdate()
            }
            DeckButton {
                text: "Releases on GitHub"; glyph: "globe"
                onClicked: Qt.openUrlExternally("https://github.com/EXPOSUREEE/Scrcpy-GUI-by-EXPOSUREEE/releases")
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Type { text: "Update preference:"; font.pixelSize: 12; quiet: true }
            Choice {
                Layout.preferredWidth: 200
                model: ["Follow latest stable", "Keep selected version"]
                currentIndex: deck.state.deckPinningPreference === "pinned" ? 1 : 0
                onActivated: index => deck.setDeckPinning(index === 1 ? "pinned" : "follow_latest")
            }
        }
    }

    /* ── SECTION B: SCRCPY CORE ENGINE ── */
    Card {
        visible: page.section === "Updates"; title: "Scrcpy core engine updates"; glyph: "tools"
        Type {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: "Scrcpy is the screen and camera mirroring engine by Genymobile. Manage engine versions, switch between local runtimes, or download newer versions directly into your runtime."
            quiet: true
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 16
            ColumnLayout {
                spacing: 2
                Type { text: "Active runtime"; font.pixelSize: 12; quiet: true }
                Type { text: "v" + (deck.state.scrcpyVersion || deck.scrcpy_version); font.weight: Font.DemiBold; font.pixelSize: 15 }
            }
            Rectangle { implicitWidth: 1; implicitHeight: 32; color: Theme.line }
            ColumnLayout {
                spacing: 2
                Type { text: "Latest stable"; font.pixelSize: 12; quiet: true }
                Type {
                    text: deck.state.scrcpyStatus === "checking" ? "Checking…"
                        : deck.state.scrcpyStatus === "error" ? "Check failed"
                        : deck.state.scrcpyLatest ? ("v" + deck.state.scrcpyLatest
                            + (deck.state.scrcpyStatus === "offline" ? " (Cached — offline)"
                               : deck.state.scrcpyStatus === "available" ? " (Update available)" : " (Up to date)"))
                        : "Not checked"
                    color: deck.state.scrcpyStatus === "available" ? Theme.accent : Theme.text
                    font.weight: Font.DemiBold; font.pixelSize: 15
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; spacing: 4
            Type { text: "Select scrcpy version"; font.pixelSize: 12; quiet: true }
            Choice {
                objectName: "scrcpyReleaseChoice"
                Layout.fillWidth: true
                model: deck.state.scrcpyReleaseLabels
                currentIndex: deck.state.selectedScrcpyIndex || 0
                onActivated: index => deck.selectScrcpyRelease(index)
            }
        }

        ColumnLayout {
            visible: !!deck.state.selectedScrcpyInfo && !!deck.state.selectedScrcpyInfo.version
            Layout.fillWidth: true; spacing: 4
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Type { text: "Selected: v" + (deck.state.selectedScrcpyInfo.version || ""); font.weight: Font.DemiBold }
                Type { text: "•"; quiet: true; visible: !!deck.state.selectedScrcpyInfo.date }
                Type { text: "Release date: " + (deck.state.selectedScrcpyInfo.date || "Unknown"); quiet: true; visible: !!deck.state.selectedScrcpyInfo.date }
                Type { text: "•"; quiet: true; visible: !!deck.state.selectedScrcpyInfo.size_str }
                Type { text: "Size: " + (deck.state.selectedScrcpyInfo.size_str || ""); quiet: true; visible: !!deck.state.selectedScrcpyInfo.size_str }
                Type { text: "•"; quiet: true }
                Type {
                    text: "Status: " + (deck.state.selectedScrcpyInfo.version === (deck.state.scrcpyVersion || deck.scrcpy_version) ? "Active runtime" : deck.state.selectedScrcpyInfo.is_installed ? "Available locally" : "Available for download")
                    color: deck.state.selectedScrcpyInfo.version === (deck.state.scrcpyVersion || deck.scrcpy_version) ? Theme.positive : Theme.accent
                    font.weight: Font.Medium
                }
            }
        }

        /* Compatibility Notice Box */
        Rectangle {
            visible: !!deck.state.scrcpyCompatibilitySummary && deck.state.scrcpyCompatibilitySummary.length > 0
            Layout.fillWidth: true
            implicitHeight: compatCol.implicitHeight + 16
            radius: 10
            color: Theme.amberSoft
            border.color: Theme.amber
            border.width: 1
            ColumnLayout {
                id: compatCol
                anchors.fill: parent; anchors.margins: 10; spacing: 4
                RowLayout {
                    spacing: 6
                    Glyph { name: "warning"; size: 16; color: Theme.amber }
                    Type {
                        text: "Compatibility notice for scrcpy v" + (deck.state.selectedScrcpyInfo.version || "") + ":"
                        font.bold: true; color: Theme.amber
                    }
                }
                Repeater {
                    model: deck.state.scrcpyCompatibilitySummary
                    Type {
                        required property string modelData
                        Layout.fillWidth: true; wrapMode: Text.Wrap
                        text: "• " + modelData
                        color: Theme.text; font.pixelSize: 12
                    }
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
        Type {
            visible: deck.state.scrcpyStatus === "offline"
            Layout.fillWidth: true; color: Theme.amber; wrapMode: Text.Wrap
            text: "Offline — showing the most recently cached scrcpy releases."
        }

        Flow {
            Layout.fillWidth: true; spacing: 8
            DeckButton {
                primary: true
                text: deck.state.scrcpyActionText || "Install"
                glyph: "download"
                enabled: (deck.state.scrcpyActionText !== "Active runtime") && (deck.state.scrcpyStatus !== "downloading") && (deck.state.scrcpyStatus !== "installing")
                onClicked: deck.installOrActivateSelectedScrcpy()
            }
            DeckButton {
                text: "View release notes"; glyph: "globe"
                visible: !!deck.state.selectedScrcpyInfo && !!deck.state.selectedScrcpyInfo.html_url
                onClicked: Qt.openUrlExternally(deck.state.selectedScrcpyInfo.html_url)
            }
            DeckButton {
                text: "Clean up unused runtimes"; glyph: "trash"
                enabled: deck.state.scrcpyStatus !== "downloading" && deck.state.scrcpyStatus !== "installing"
                onClicked: deck.cleanUnusedRuntimes()
            }
            DeckButton {
                text: "Check for updates"; glyph: "refresh"
                enabled: deck.state.scrcpyStatus !== "downloading" && deck.state.scrcpyStatus !== "installing"
                onClicked: deck.checkAllUpdates(true)
            }
            DeckButton {
                visible: deck.state.scrcpyStatus === "downloading"
                text: "Cancel"; glyph: "cancel"
                onClicked: deck.cancelScrcpyUpdate()
            }
            DeckButton {
                text: "Genymobile scrcpy repo"; glyph: "globe"
                onClicked: Qt.openUrlExternally("https://github.com/Genymobile/scrcpy/releases")
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Type { text: "Engine preference:"; font.pixelSize: 12; quiet: true }
            Choice {
                Layout.preferredWidth: 200
                model: ["Follow latest stable", "Keep selected version"]
                currentIndex: deck.state.scrcpyPinningPreference === "pinned" ? 1 : 0
                onActivated: index => deck.setScrcpyPinning(index === 1 ? "pinned" : "follow_latest")
            }
        }
    }

    /* Downgrade confirmation dialog */
    DeckDialog {
        id: downgradeDialog
        title: "Confirm Application Downgrade"
        standardButtons: Dialog.Ok | Dialog.Cancel
        ColumnLayout {
            width: parent.width; spacing: 10
            Type {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: "You are about to downgrade Scrcpy Deck to an older version.\n\nOlder versions may not support all features or settings saved by newer versions. Your current settings have been safely backed up to your profile directory."
            }
            Type {
                Layout.fillWidth: true; font.bold: true; color: Theme.accent
                text: "Target version: v" + (deck.state.selectedDeckInfo ? deck.state.selectedDeckInfo.version : "")
            }
        }
        onAccepted: {
            deck.installSelectedDeck(true)
        }
    }

    /* ── OTHER SECTIONS PRESERVED UNCHANGED ── */
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
