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
            model: ["USB debugging", "Resources", "Videos", "FAQ"]
            DeckButton { required property string modelData; text: modelData; selected: page.section === text; onClicked: page.section = text }
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
