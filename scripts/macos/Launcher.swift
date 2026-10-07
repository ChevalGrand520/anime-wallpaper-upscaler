import AppKit

// A small document-opening front end. Python remains the only wallpaper workflow implementation.
final class Launcher: NSObject, NSApplicationDelegate {
    private var receivedDocuments = false
    private var pending: [String] = []
    private var processing = false
    private var statusWindow: NSWindow?
    private var statusLabel: NSTextField?
    private let taskLock = NSLock()
    private var activeTask: Process?
    private var cancelling = false

    private var root: String {
        Bundle.main.object(forInfoDictionaryKey: "AnimeWallpaperUpscalerProject") as? String ?? ""
    }

    private func invoke(_ arguments: [String], cancellable: Bool = false) -> (Int32, String) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: root).appendingPathComponent(".venv/bin/python")
        task.arguments = [root + "/scripts/macos_launcher.py"] + arguments
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe
        do {
            if cancellable { taskLock.lock() }
            try task.run()
            if cancellable {
                activeTask = task
                if cancelling { task.terminate() }
                taskLock.unlock()
            }
            let output = pipe.fileHandleForReading.readDataToEndOfFile()
            task.waitUntilExit()
            if cancellable {
                taskLock.lock()
                activeTask = nil
                taskLock.unlock()
            }
            return (task.terminationStatus, String(data: output, encoding: .utf8) ?? "")
        } catch {
            if cancellable { taskLock.unlock() }
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
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 380, height: 150),
                              styleMask: [.titled], backing: .buffered, defer: false)
        window.title = "Anime Wallpaper Upscaler"
        window.isReleasedWhenClosed = false
        let label = NSTextField(labelWithString: "Processing \(paths.count) input(s) at \(currentScale())x…")
        label.frame = NSRect(x: 24, y: 110, width: 332, height: 24)
        let spinner = NSProgressIndicator(frame: NSRect(x: 24, y: 80, width: 332, height: 16))
        spinner.style = .bar
        spinner.isIndeterminate = true
        spinner.startAnimation(nil)
        window.contentView?.addSubview(label)
        window.contentView?.addSubview(spinner)
        let cancel = NSButton(title: "Cancel & Delete This Run's Outputs", target: self,
                              action: #selector(cancelRun))
        cancel.frame = NSRect(x: 24, y: 20, width: 332, height: 32)
        window.contentView?.addSubview(cancel)
        statusLabel = label
        statusWindow = window
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        DispatchQueue.global(qos: .userInitiated).async {
            let result = self.invoke(["--"] + paths, cancellable: true)
            DispatchQueue.main.async {
                self.processing = false
                self.statusWindow?.close()
                self.statusWindow = nil
                if result.0 != 0 && result.0 != 130 && !(self.cancelling && result.0 == -15) {
                    self.showError(result.1)
                }
                if self.pending.isEmpty { NSApp.terminate(nil) }
                else { self.processNext() }
            }
        }
    }

    @objc private func cancelRun() {
        guard processing else { return }
        pending.removeAll()
        statusLabel?.stringValue = "Cancelling… deleting this run's outputs."
        taskLock.lock()
        cancelling = true
        if let task = activeTask, task.isRunning { task.terminate() }
        taskLock.unlock()
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if processing {
            cancelRun()
            return .terminateCancel
        }
        return .terminateNow
    }
}

let application = NSApplication.shared
let delegate = Launcher()
application.delegate = delegate
application.setActivationPolicy(.regular)
let mainMenu = NSMenu()
let applicationItem = NSMenuItem()
let applicationMenu = NSMenu(title: "Anime Wallpaper Upscaler")
let quitItem = NSMenuItem(title: "Quit Anime Wallpaper Upscaler",
                          action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
quitItem.target = application
applicationMenu.addItem(quitItem)
applicationItem.submenu = applicationMenu
mainMenu.addItem(applicationItem)
application.mainMenu = mainMenu
application.run()
