import AppKit

// A small document-opening front end. Python remains the only wallpaper workflow implementation.
final class Launcher: NSObject, NSApplicationDelegate {
    private var receivedDocuments = false
    private var pending: [String] = []
    private var processing = false
    private var statusWindow: NSWindow?
    private var statusLabel: NSTextField?

    private var root: String {
        Bundle.main.object(forInfoDictionaryKey: "AnimeWallpaperUpscalerProject") as? String ?? ""
    }

    private func invoke(_ arguments: [String]) -> (Int32, String) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: root).appendingPathComponent(".venv/bin/python")
        task.arguments = [root + "/scripts/macos_launcher.py"] + arguments
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe
        do {
            try task.run()
            let output = pipe.fileHandleForReading.readDataToEndOfFile()
            task.waitUntilExit()
            return (task.terminationStatus, String(data: output, encoding: .utf8) ?? "")
        } catch {
            return (2, "Could not start the local runtime. Rerun install.command.\n" + error.localizedDescription)
        }
    }

    private func currentScale() -> String {
        let result = invoke(["--get-scale"])
        let value = result.1.trimmingCharacters(in: .whitespacesAndNewlines)
        return ["2", "3", "4"].contains(value) ? value : "4"
    }

    private func showError(_ text: String) {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = "Wallpaper processing failed"
        alert.informativeText = String(text.suffix(1800))
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Initial document events arrive around launch. Defer the picker until they are delivered.
        DispatchQueue.main.async {
            if !self.receivedDocuments { self.showMenu() }
        }
    }

    func application(_ sender: NSApplication, openFiles filenames: [String]) {
        receivedDocuments = true
        pending += filenames
        sender.reply(toOpenOrPrint: .success)
        if NSApp.modalWindow != nil { NSApp.abortModal() }
        if !processing { processNext() }
    }

    private func showMenu() {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = "Anime Wallpaper Upscaler"
        alert.informativeText = "Drop images or folders onto this app to process them at \(currentScale())x. Results open in Finder."
        alert.addButton(withTitle: "Choose Images or Folders…")
        alert.addButton(withTitle: "Scale…")
        alert.addButton(withTitle: "Cancel")
        switch alert.runModal() {
        case .alertFirstButtonReturn:
            let picker = NSOpenPanel()
            picker.canChooseFiles = true
            picker.canChooseDirectories = true
            picker.allowsMultipleSelection = true
            picker.message = "Choose wallpaper images or folders"
            if picker.runModal() == .OK {
                pending += picker.urls.map { $0.path }
                processNext()
            } else { NSApp.terminate(nil) }
        case .alertSecondButtonReturn: showScaleSettings()
        default: NSApp.terminate(nil)
        }
    }

    private func showScaleSettings() {
        let alert = NSAlert()
        alert.messageText = "Upscale Factor"
        alert.informativeText = "Used for future drops and Terminal launches."
        let choices = NSPopUpButton(frame: NSRect(x: 0, y: 0, width: 160, height: 28))
        choices.addItems(withTitles: ["2x", "3x", "4x"])
        choices.selectItem(withTitle: currentScale() + "x")
        alert.accessoryView = choices
        alert.addButton(withTitle: "Save")
        alert.addButton(withTitle: "Cancel")
        if alert.runModal() == .alertFirstButtonReturn {
            let selected = String(choices.titleOfSelectedItem?.prefix(1) ?? "4")
            let result = invoke(["--set-scale", selected])
            if result.0 != 0 { showError(result.1) }
        }
        NSApp.terminate(nil)
    }

    private func processNext() {
        guard !pending.isEmpty else { NSApp.terminate(nil); return }
        let paths = pending
        pending.removeAll()
        processing = true
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 380, height: 110),
                              styleMask: [.titled], backing: .buffered, defer: false)
        window.title = "Anime Wallpaper Upscaler"
        window.isReleasedWhenClosed = false
        let label = NSTextField(labelWithString: "Processing \(paths.count) input(s) at \(currentScale())x…")
        label.frame = NSRect(x: 24, y: 65, width: 332, height: 24)
        let spinner = NSProgressIndicator(frame: NSRect(x: 24, y: 30, width: 332, height: 16))
        spinner.style = .bar
        spinner.isIndeterminate = true
        spinner.startAnimation(nil)
        window.contentView?.addSubview(label)
        window.contentView?.addSubview(spinner)
        statusLabel = label
        statusWindow = window
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        DispatchQueue.global(qos: .userInitiated).async {
            let result = self.invoke(["--"] + paths)
            DispatchQueue.main.async {
                self.processing = false
                self.statusWindow?.close()
                self.statusWindow = nil
                if result.0 != 0 { self.showError(result.1) }
                if self.pending.isEmpty { NSApp.terminate(nil) }
                else { self.processNext() }
            }
        }
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        // Prevent leaving an inference child behind by closing its parent mid-run.
        if processing {
            statusLabel?.stringValue = "Processing… Results will open in Finder."
            return .terminateCancel
        }
        return .terminateNow
    }
}

let application = NSApplication.shared
let delegate = Launcher()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
