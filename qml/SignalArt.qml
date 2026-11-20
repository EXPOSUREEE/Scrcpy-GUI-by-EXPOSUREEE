// Static connection illustration. Only size changes invalidate the texture.
import QtQuick
Canvas {
    id: art
    Accessible.ignored: true
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        const c = getContext("2d")
        c.reset()
        c.scale(width / 300, height / 178)
        c.strokeStyle = "#33554d"
        c.lineWidth = 0.7
        for (let i = 0; i < 6; ++i) {
            c.beginPath()
            c.ellipse(20-i*13, 40-i*13, 218+i*26, 110+i*26)
            c.stroke()
        }
        for (let x = 8; x < 298; x += 13)
            for (let y = 6; y < 178; y += 13) {
                c.fillStyle = "#47655c"; c.fillRect(x, y, 1, 1)
            }
        function phone(x, y, angle, rear) {
            c.save(); c.translate(x,y); c.rotate(angle)
            let g = c.createLinearGradient(0,0,80,139)
            g.addColorStop(0, rear ? "#44675e" : "#53786e")
            g.addColorStop(1, "#172b2a")
            c.fillStyle=g; c.strokeStyle=rear ? "#759d8e" : "#c1e2d0"; c.lineWidth=1.5
            c.beginPath(); c.roundedRect(0,0,75,137,11,11); c.fill(); c.stroke()
            c.save()
            c.beginPath(); c.roundedRect(4,4,67,129,8,8); c.clip()
            let screen = c.createLinearGradient(4,4,65,133)
            screen.addColorStop(0,rear ? "#314c48" : "#28443f")
            screen.addColorStop(0.6,rear ? "#24433b" : "#3f7a60")
            screen.addColorStop(1,"#152b29")
            c.fillStyle=screen; c.fillRect(4,4,67,129)
            for (let i=0;i<21;i++) {
                c.strokeStyle=rear ? "#537967" : (i%5===0 ? "#b3e9b7" : "#83b998")
                c.lineWidth=0.66; c.beginPath(); c.moveTo(-7,35+i*3.2)
                c.bezierCurveTo(16,45+i*3.1,25,118-i*1.6,86,66+i*3.7); c.stroke()
            }
            c.restore()
            c.fillStyle="#132721"; c.beginPath(); c.roundedRect(24,5,27,4,2,2); c.fill()
            c.fillStyle="#c0ddc7"; c.fillRect(28,129,20,1.5)
            c.restore()
        }
        phone(88,27,-0.20,true)
        phone(163,18,0.18,false)
        c.fillStyle="#c0efb8"
        for (let p of [[54,109],[260,66],[233,153]]) {
            c.beginPath(); c.arc(p[0],p[1],2,0,2*Math.PI); c.fill()
        }
    }
}
