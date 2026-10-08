pragma Singleton

import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Io

/*
 * System updates service for pacman/checkupdates and XBPS.
 */
Singleton {
    id: root

    property bool available: false
    property int count: 0
    property string _backend: ""
    property string _availabilityOutput: ""
    
    readonly property bool updateAdvised: available && count > (Config.options?.updates?.adviseUpdateThreshold ?? 75)
    readonly property bool updateStronglyAdvised: available && count > (Config.options?.updates?.stronglyAdviseUpdateThreshold ?? 200)

    function load() {}
    function refresh() {
        if (!available) return;
        print("[Updates] Checking for system updates")
        checkUpdatesProc.command = root._backend === "xbps"
            ? ["xbps-install", "-nu"]
            : ["checkupdates"]
        checkUpdatesProc.running = true;
    }

    Timer {
        interval: (Config.options?.updates?.checkInterval ?? 120) * 60 * 1000
        repeat: true
        running: Config.ready
        onTriggered: {
            print("[Updates] Periodic update check due")
            root.refresh();
        }
    }

    Timer {
        id: availabilityDefer
        interval: 1500
        repeat: false
        onTriggered: {
            root._availabilityOutput = ""
            checkAvailabilityProc.running = true
        }
    }

    Connections {
        target: Config
        function onReadyChanged() {
            if (Config.ready) availabilityDefer.start()
        }
    }

    Component.onCompleted: if (Config.ready) availabilityDefer.start()

    Process {
        id: checkAvailabilityProc
        running: false
        command: ["/usr/bin/bash", "-c",
            "if command -v checkupdates &>/dev/null; then printf 'pacman\\n'; " +
            "elif command -v xbps-install &>/dev/null; then printf 'xbps\\n'; " +
            "else exit 1; fi"
        ]
        stdout: SplitParser {
            splitMarker: ""
            onRead: data => { root._availabilityOutput += data }
        }
        onExited: (exitCode, exitStatus) => {
            root._backend = exitCode === 0 ? root._availabilityOutput.trim() : ""
            root.available = root._backend.length > 0
            root.refresh();
        }
    }

    Process {
        id: checkUpdatesProc
        command: []
        stdout: StdioCollector {
            onStreamFinished: {
                const t = (text ?? "").trim();
                root.count = t.length > 0 ? t.split("\n").length : 0;
            }
        }
        onExited: (exitCode, exitStatus) => {
            // checkupdates exits 2 when the system is already up to date.
            if (exitCode === 2) {
                root.count = 0
                return
            }
            if (exitCode !== 0) {
                console.error("[Updates] update check failed for", root._backend, exitCode, exitStatus)
            }
        }
    }
}
