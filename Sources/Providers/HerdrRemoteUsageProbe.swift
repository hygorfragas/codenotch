import Darwin
import Foundation
import os

/// Saved Herdr SSH machine. Settings still do not list these; the probe uses
/// them only to reach the remote Herdr server.
struct HerdrSavedMachine: Equatable, Sendable, Decodable {
    let id: String
    let label: String
    let target: String
    let enabled: Bool
}

/// One live agent pane reported by a remote `herdr agent list`.
struct HerdrRemoteAgent: Equatable, Sendable {
    let machine: HerdrSavedMachine
    let herdrAgent: String
    var familyID: String? { HerdrRemoteUsageProbe.familyID(forHerdrAgent: herdrAgent) }
}

/// Reads extra usage from agents Herdr already sees on a remote machine.
///
/// Inventory comes from `herdr agent list` on the SSH target. Local
/// `~/.claude-<slug>` profiles stay local rings and are never treated as
/// remote connections.
struct HerdrRemoteUsageProbe: Sendable {
    var herdrURL: URL?
    var sshURL: URL
    var listMachines: @Sendable () throws -> Data
    var listAgents: @Sendable (String) throws -> Data
    var readUsage: @Sendable (String) throws -> String

    static let timeout: TimeInterval = 25

    init(
        herdrURL: URL? = locateHerdr(),
        sshURL: URL = URL(fileURLWithPath: "/usr/bin/ssh"),
        listMachines: (@Sendable () throws -> Data)? = nil,
        listAgents: (@Sendable (String) throws -> Data)? = nil,
        readUsage: (@Sendable (String) throws -> String)? = nil
    ) {
        self.herdrURL = herdrURL
        self.sshURL = sshURL
        let binary = herdrURL
        self.listMachines = listMachines ?? {
            guard let binary else { throw UsageProviderError.badResponse(status: 0) }
            return try HerdrRemoteUsageProbe.runHerdrList(binary: binary)
        }
        let ssh = sshURL
        self.listAgents = listAgents ?? { target in
            try HerdrRemoteUsageProbe.runSSH(ssh: ssh, target: target, script: HerdrRemoteUsageProbe.remoteAgentListScript)
        }
        self.readUsage = readUsage ?? { target in
            let data = try HerdrRemoteUsageProbe.runSSH(ssh: ssh, target: target, script: HerdrRemoteUsageProbe.remoteUsageScript)
            guard let text = String(data: data, encoding: .utf8),
                  !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw UsageProviderError.badResponse(status: 0)
            }
            return text
        }
    }

    static func locateHerdr(
        home: URL = URL(fileURLWithPath: NSHomeDirectory()),
        root: URL = URL(fileURLWithPath: "/"),
        fileManager: FileManager = .default
    ) -> URL? {
        let candidates = [
            home.appendingPathComponent(".local/bin/herdr"),
            root.appendingPathComponent("opt/homebrew/bin/herdr"),
            root.appendingPathComponent("usr/local/bin/herdr"),
        ]
        return candidates.first { fileManager.isExecutableFile(atPath: $0.path) }
    }

    static func familyID(forHerdrAgent agent: String) -> String? {
        switch agent {
        case "claude": return ClaudeProfile.defaultID
        case "codex": return CodexProfile.defaultID
        case "cursor": return "cursor"
        default: return nil
        }
    }

    static func parseMachines(_ data: Data) throws -> [HerdrSavedMachine] {
        try JSONDecoder().decode([HerdrSavedMachine].self, from: data)
    }

    static func parseAgentList(_ data: Data) throws -> [String] {
        let envelope = try JSONDecoder().decode(HerdrAgentListEnvelope.self, from: data)
        return envelope.result.agents.compactMap(\.agent)
    }

    func liveAgents() -> [HerdrRemoteAgent] {
        let machines = (try? Self.parseMachines(try listMachines()).filter(\.enabled)) ?? []
        guard !machines.isEmpty else { return [] }
        let lock = NSLock()
        var found: [HerdrRemoteAgent] = []
        DispatchQueue.concurrentPerform(iterations: machines.count) { index in
            let machine = machines[index]
            do {
                let kinds = try Self.parseAgentList(try listAgents(machine.target))
                lock.lock()
                for kind in Set(kinds) {
                    found.append(HerdrRemoteAgent(machine: machine, herdrAgent: kind))
                }
                lock.unlock()
            } catch {
                Log.usage.error("herdr agent list missed on \(machine.label, privacy: .public): \(String(describing: error), privacy: .public)")
            }
        }
        return found
    }

    func liveConnections() -> [RemoteUsageConnection] {
        connections(from: liveAgents())
    }

    func connections(from agents: [HerdrRemoteAgent]) -> [RemoteUsageConnection] {
        var seen = Set<String>()
        var connections: [RemoteUsageConnection] = []
        for agent in agents {
            guard let family = agent.familyID else { continue }
            let connection = RemoteUsageConnection(
                assistantID: family,
                connectionName: agent.machine.label
            )
            guard seen.insert(connection.id).inserted else { continue }
            connections.append(connection)
        }
        return connections
    }

    func readEnabled(from agents: [HerdrRemoteAgent]? = nil) async -> [RemoteUsageReading] {
        let agents = (agents ?? liveAgents()).filter { $0.familyID == ClaudeProfile.defaultID }
        return await withTaskGroup(of: RemoteUsageReading?.self) { group in
            for agent in agents {
                let readUsage = self.readUsage
                group.addTask {
                    await HerdrRemoteUsageProbe.readClaudeUsage(
                        machine: agent.machine,
                        readUsage: readUsage
                    )
                }
            }
            var readings: [RemoteUsageReading] = []
            for await reading in group {
                if let reading { readings.append(reading) }
            }
            return readings
        }
    }

    private static func readClaudeUsage(
        machine: HerdrSavedMachine,
        readUsage: @escaping @Sendable (String) throws -> String
    ) async -> RemoteUsageReading? {
        do {
            let text = try await withCheckedThrowingContinuation { continuation in
                DispatchQueue.global(qos: .utility).async {
                    continuation.resume(with: Result { try readUsage(machine.target) })
                }
            }
            let windows = try ClaudeUsageCLI.parse(text)
            return RemoteUsageReading(
                connection: RemoteUsageConnection(
                    assistantID: ClaudeProfile.defaultID,
                    connectionName: machine.label
                ),
                windows: windows,
                plan: ClaudeUsageCLI.plan(in: text),
                fetchedAt: Date()
            )
        } catch {
            Log.usage.debug("remote \(machine.label, privacy: .public) claude usage missed")
            return nil
        }
    }

    private static func runHerdrList(binary: URL) throws -> Data {
        try runLocal(binary: binary, arguments: ["machine", "list", "--json"], timeout: 8)
    }

    static let remoteAgentListScript = """
    set +e
    export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
    for h in "$HOME/.local/bin/herdr" /opt/homebrew/bin/herdr /usr/local/bin/herdr; do
      if [ -x "$h" ]; then
        exec "$h" agent list
      fi
    done
    if command -v herdr >/dev/null 2>&1; then
      exec herdr agent list
    fi
    exit 127
    """

    static let remoteUsageScript = """
    set +e
    for c in "$HOME/.local/bin/claude" "$HOME/.claude/local/claude" "$HOME/.bun/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
      if [ -x "$c" ]; then
        exec "$c" --print --no-session-persistence --strict-mcp-config /usage
      fi
    done
    newest=$(ls -1d "$HOME/.nvm/versions/node/"*/bin/claude 2>/dev/null | sort -V | tail -1)
    if [ -n "$newest" ] && [ -x "$newest" ]; then
      exec "$newest" --print --no-session-persistence --strict-mcp-config /usage
    fi
    exit 127
    """

    /// ssh joins extra argv with spaces. The script must stay one argument or
    /// the remote shell runs `set` / `bash -s` with an empty stdin and hangs.
    static func sshArguments(target: String, command: String) -> [String] {
        [
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=8",
            "-o", "ConnectionAttempts=1",
            "-o", "LogLevel=ERROR",
            target,
            command,
        ]
    }

    private static func runSSH(ssh: URL, target: String, script: String) throws -> Data {
        let process = Process()
        process.executableURL = ssh
        process.arguments = sshArguments(target: target, command: script)
        var environment = ProcessInfo.processInfo.environment
        environment["HOME"] = NSHomeDirectory()
        environment["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        process.environment = environment
        return try runCapturing(process, timeout: timeout)
    }

    private static func runLocal(binary: URL, arguments: [String], timeout: TimeInterval) throws -> Data {
        let process = Process()
        process.executableURL = binary
        process.arguments = arguments
        return try runCapturing(process, timeout: timeout)
    }

    private static func runCapturing(_ process: Process, timeout: TimeInterval) throws -> Data {
        let output = Pipe()
        process.standardInput = FileHandle.nullDevice
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        try process.run()
        let pid = process.processIdentifier
        let finished = DispatchGroup()
        finished.enter()
        DispatchQueue.global(qos: .utility).async {
            process.waitUntilExit()
            finished.leave()
        }
        if finished.wait(timeout: .now() + timeout) == .timedOut {
            kill(pid, SIGKILL)
            process.waitUntilExit()
            throw UsageProviderError.badResponse(status: 137)
        }
        let data = output.fileHandleForReading.readDataToEndOfFile()
        guard process.terminationStatus == 0 else {
            throw UsageProviderError.badResponse(status: Int(process.terminationStatus))
        }
        guard !data.isEmpty else { throw UsageProviderError.badResponse(status: 0) }
        return data
    }
}

private struct HerdrAgentListEnvelope: Decodable {
    let result: Result

    struct Result: Decodable {
        let agents: [Agent]
    }

    struct Agent: Decodable {
        let agent: String?
    }
}
