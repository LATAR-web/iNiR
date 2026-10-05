pragma ComponentBehavior: Bound

import QtQuick
import qs.modules.common.functions
import qs.modules.iris.style

// Graded once into a texture so the desktop costs no more at rest than a plain image. Two slots: the new picture is
// graded in the idle one and fades in; the old one then lets its picture go.
Item {
    id: root

    property string imagePath: ""
    property int fillMode: Image.PreserveAspectCrop
    property real devicePixelRatio: 1

    component Slot: Item {
        id: slot
        anchors.fill: parent
        property string path: ""
        readonly property bool ready: slot.path.length > 0 && picture.status === Image.Ready && small.status === Image.Ready
        signal captured()

        Image {
            id: picture
            anchors.fill: parent
            visible: false
            asynchronous: true
            cache: false
            source: slot.path.length > 0 ? "file://" + FileUtils.trimFileProtocol(slot.path) : ""
            fillMode: root.fillMode
            sourceSize: root.fillMode === Image.Tile || root.fillMode === Image.Pad ? Qt.size(0, 0)
                : Qt.size(Math.ceil(root.width * root.devicePixelRatio), Math.ceil(root.height * root.devicePixelRatio))
        }
        // The bloom's source: the same picture decoded small, so the spill is a few taps instead of a blur pass.
        Image {
            id: small
            anchors.fill: parent
            visible: false
            asynchronous: true
            cache: false
            source: picture.source
            fillMode: root.fillMode
            sourceSize: Qt.size(Math.max(16, Math.ceil(root.width / 14)), Math.max(16, Math.ceil(root.height / 14)))
        }
        ShaderEffect {
            id: graded
            anchors.fill: parent
            fragmentShader: Qt.resolvedUrl("IrisAfterglowWallpaper.frag.qsb")
            readonly property Item source: picture
            readonly property Item glow: small
            readonly property vector4d glowMix: IrisStyle.afterglowMix
            readonly property vector4d glowShadow: IrisStyle.afterglowShadow
            readonly property vector4d glowLight: IrisStyle.afterglowLight
            readonly property vector4d glowBloom: IrisStyle.afterglowBloomInk
            readonly property vector4d frame: Qt.vector4d(Math.max(1, root.width), Math.max(1, root.height),
                1.6 / Math.max(16, Math.ceil(root.width / 14)), 0)
            onGlowMixChanged: settle.restart()
            onGlowShadowChanged: settle.restart()
            onGlowLightChanged: settle.restart()
            onGlowBloomChanged: settle.restart()
        }
        ShaderEffectSource {
            id: cache
            anchors.fill: parent
            sourceItem: graded
            hideSource: true
            live: false
        }
        // One capture per change of picture, size or grade, after a resize has settled; never per frame.
        Timer {
            id: settle
            interval: 120
            onTriggered: {
                if (!slot.ready || root.width < 1 || root.height < 1) return
                cache.scheduleUpdate()
                slot.captured()
            }
        }
        onReadyChanged: if (slot.ready) settle.restart()
        onWidthChanged: settle.restart()
        onHeightChanged: settle.restart()
    }

    property int front: 0
    readonly property Slot frontSlot: root.front === 0 ? slotA : slotB
    readonly property Slot backSlot: root.front === 0 ? slotB : slotA
    onImagePathChanged: {
        if (root.imagePath === root.frontSlot.path) return
        root.backSlot.path = root.imagePath
    }
    Component.onCompleted: root.frontSlot.path = root.imagePath

    function arrived(slot: Item): void {
        if (slot !== root.frontSlot) {
            root.front = 1 - root.front
            slot.z = 1
            root.backSlot.z = 0
        } else if (slot.opacity >= 1) {
            return
        }
        if (IrisStyle.motionEnabled) {
            arrive.target = slot
            arrive.restart()
        } else {
            slot.opacity = 1
            root.release()
        }
    }
    function release(): void {
        if (root.backSlot.path === root.imagePath) return
        root.backSlot.opacity = 0
        root.backSlot.path = ""
    }
    Slot { id: slotA; opacity: 0; onCaptured: root.arrived(slotA) }
    Slot { id: slotB; opacity: 0; onCaptured: root.arrived(slotB) }
    NumberAnimation {
        id: arrive
        property: "opacity"
        from: 0
        to: 1
        duration: IrisStyle.duration(700)
        easing.type: Easing.OutCubic
        onFinished: root.release()
    }
}
