import Combine
import XCTest
@testable import Codenotch

/// Remote extra rings are a separate reading of the same assistant. Settings
/// still toggles the assistant id; the extra cell must not leak when that
/// assistant is off, even if a remote session exists.
@MainActor
final class RemoteUsageTests: XCTestCase {
    private func makeStore(_ providers: [UsageProvider], disconnected: Set<String> = [],
                           archive: UsageArchive? = nil,
                           remoteConnections: [RemoteUsageConnection] = []) -> UsageStore {
        let name = "RemoteUsageTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let archive = archive ?? UsageArchive(defaults: defaults)
        return UsageStore(providers: providers, archive: archive, disconnected: disconnected,
                          remoteConnections: remoteConnections)
    }

    private func phoneSnapshot(from store: UsageStore, disconnected: Set<String> = [],
                               at now: Date = Date()) -> PhoneLinkSnapshot {
        PhoneLinkSnapshotBuilder.build(
            snapshots: store.notchSnapshots,
            sessions: [],
            disconnected: disconnected,
            order: [],
            serverName: "test",
            serverVersion: "0",
            now: now
        )
    }

    private func extraRemoteRings(in store: UsageStore) -> [ProviderSnapshot] {
        store.notchSnapshots.filter(\.isRemoteExtraReading)
    }

    private func rememberedRemote(id: String, name: String, fraction: Double,
                                  fetchedAt: Date) -> ProviderSnapshot {
        ProviderSnapshot(
            id: id, displayName: name, glyph: .claude,
            fidelity: .official, status: .ok,
            windows: [LimitWindow(id: "session", label: "Session", usedFraction: fraction,
                                  resetsAt: Date().addingTimeInterval(3600))]
        )
    }

    // SPECSFY: US-001 US-002 FR-001 NFR-003 AC-001
    func testDisabledRemoteAssistantDoesNotPublishAnExtraRing() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let remoteSession = RemoteUsageProbe(id: "claude:Office", connectionName: "Office")
        let store = makeStore([assistant, remoteSession], disconnected: [assistant.id])

        XCTAssertFalse(
            store.notchSnapshots.contains { $0.id == remoteSession.id },
            "an extra remote ring appeared while the assistant was off in Settings"
        )
        XCTAssertFalse(
            store.notchSnapshots.contains { $0.id == assistant.id },
            "the local assistant ring also has to stay off"
        )
    }

    // SPECSFY: US-001 US-002 FR-001 FR-005 NFR-002 AC-002
    func testUnavailableRemoteSessionShowsAnEmptyExtraRing() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Office")]
        )

        guard let extra = store.notchSnapshots.first(where: { $0.id == "claude:Office" }) else {
            XCTFail("an extra remote ring should appear once the assistant is on, even before a good reading")
            return
        }
        XCTAssertFalse(
            extra.hasReading,
            "the first remote ring must have no number until a good reading exists"
        )
    }

    // SPECSFY: US-001 FR-005 NFR-002 AC-003
    func testUnavailableRemoteSessionKeepsTheLastQuotaMarkedStale() {
        let name = "RemoteUsageTests.stale.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let archive = UsageArchive(defaults: defaults)
        let fetchedAt = Date().addingTimeInterval(-600)
        let remembered = ProviderSnapshot(
            id: "claude:Office", displayName: "Office", glyph: .claude,
            fidelity: .official, status: .ok,
            windows: [LimitWindow(id: "session", label: "Session", usedFraction: 0.42,
                                  resetsAt: Date().addingTimeInterval(3600))]
        )
        archive.save(["claude:Office": (remembered, fetchedAt)])

        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = UsageStore(providers: [assistant], archive: archive, disconnected: [])

        guard let extra = store.notchSnapshots.first(where: { $0.id == "claude:Office" }) else {
            XCTFail("after a good remote reading, the extra ring must stay when the session goes quiet")
            return
        }
        XCTAssertTrue(extra.status.isStale, "the last remote quota must be marked stale")
        XCTAssertEqual(extra.usedFraction, 0.42)
    }

    // SPECSFY: US-001 FR-002 FR-003 NFR-002 AC-004
    func testTwoRemoteConnectionsShareTheGlyphAndKeepNamesOffTheRing() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [
                RemoteUsageConnection(assistantID: "claude", connectionName: "Office"),
                RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")
            ]
        )
        let remotes = extraRemoteRings(in: store)

        XCTAssertEqual(remotes.count, 2, "Claude on two remote connections must draw two extra rings")
        XCTAssertTrue(remotes.allSatisfy { $0.glyph == .claude }, "both extra rings use the assistant glyph")
        XCTAssertFalse(
            remotes.contains { $0.displayName == "Office" || $0.displayName == "Lab" },
            "the connection name belongs on the tooltip, not the ring"
        )
    }

    // SPECSFY: US-003 FR-002 FR-006 NFR-001 AC-005
    func testPhoneTapShowsRemoteNameQuotaAndResetWithoutSecrets() throws {
        let name = "RemoteUsageTests.phone.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let archive = UsageArchive(defaults: defaults)
        let fetchedAt = Date().addingTimeInterval(-600)
        archive.save([
            "claude:Office": (rememberedRemote(id: "claude:Office", name: "Office",
                                               fraction: 0.42, fetchedAt: fetchedAt), fetchedAt)
        ])
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            archive: archive,
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Office")]
        )
        let snapshot = phoneSnapshot(from: store)
        guard let remote = snapshot.providers.first(where: { $0.id == "claude:Office" }) else {
            XCTFail("the phone snapshot must include the remote reading already on the notch")
            return
        }
        XCTAssertEqual(remote.displayName, "Office")
        XCTAssertNotNil(remote.windows.first?.usedFraction)
        XCTAssertNotNil(remote.windows.first?.resetsAt)
        let body = String(data: try JSONEncoder().encode(snapshot), encoding: .utf8) ?? ""
        XCTAssertFalse(body.contains("sk-"), "snapshot must not carry API keys")
        XCTAssertFalse(body.contains("conversation"), "snapshot must not carry conversation")
    }

    // SPECSFY: US-002 FR-004 NFR-003 AC-006
    func testHerdrOffDoesNotDropAnActiveRemoteReading() {
        let name = "RemoteUsageTests.herdrOff.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let preferences = Preferences(defaults: defaults)
        preferences.herdrEnabled = false
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Office")]
        )
        XCTAssertFalse(preferences.herdrEnabled)
        XCTAssertNotNil(
            store.notchSnapshots.first(where: { $0.id == "claude:Office" }),
            "turning Herdr off must not remove a remote reading that is already active"
        )
    }

    // SPECSFY: US-003 FR-001 FR-006 NFR-001 AC-007
    func testPhoneSnapshotOmitsADisabledRemoteAssistant() throws {
        let remote = ProviderSnapshot(
            id: "claude:Office", displayName: "Office", glyph: .claude,
            fidelity: .official, status: .ok,
            windows: [LimitWindow(id: "session", label: "Session", usedFraction: 0.42)]
        )
        let snapshot = PhoneLinkSnapshotBuilder.build(
            snapshots: [remote],
            sessions: [],
            disconnected: ["claude"],
            order: [],
            serverName: "test",
            serverVersion: "0",
            now: Date()
        )
        XCTAssertFalse(
            snapshot.providers.contains { $0.id == "claude:Office" },
            "a remote extra cell must not reach the phone when the assistant is off"
        )
        let body = String(data: try JSONEncoder().encode(snapshot), encoding: .utf8) ?? ""
        XCTAssertFalse(body.contains("sk-"))
        XCTAssertFalse(body.contains("conversation"))
    }

    // SPECSFY: US-003 FR-005 FR-006 NFR-001 AC-008
    func testPhoneSnapshotMirrorsAStaleRemoteQuota() {
        let name = "RemoteUsageTests.phoneStale.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let archive = UsageArchive(defaults: defaults)
        let fetchedAt = Date().addingTimeInterval(-600)
        archive.save([
            "claude:Office": (rememberedRemote(id: "claude:Office", name: "Office",
                                               fraction: 0.42, fetchedAt: fetchedAt), fetchedAt)
        ])
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            archive: archive,
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Office")]
        )
        let snapshot = phoneSnapshot(from: store)
        guard let remote = snapshot.providers.first(where: { $0.id == "claude:Office" }) else {
            XCTFail("the phone must show the stale remote quota the notch already holds")
            return
        }
        XCTAssertEqual(remote.status.kind, "stale")
        XCTAssertNotNil(remote.windows.first?.usedFraction)
    }

    // SPECSFY: US-001 FR-002 FR-003 NFR-002 AC-009
    func testTwoRemoteConnectionsDoNotMixQuotas() {
        let name = "RemoteUsageTests.mix.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let archive = UsageArchive(defaults: defaults)
        let fetchedAt = Date().addingTimeInterval(-600)
        archive.save([
            "claude:Office": (rememberedRemote(id: "claude:Office", name: "Office",
                                               fraction: 0.42, fetchedAt: fetchedAt), fetchedAt),
            "claude:Lab": (rememberedRemote(id: "claude:Lab", name: "Lab",
                                                fraction: 0.77, fetchedAt: fetchedAt), fetchedAt)
        ])
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            archive: archive,
            remoteConnections: [
                RemoteUsageConnection(assistantID: "claude", connectionName: "Office"),
                RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")
            ]
        )
        let remotes = extraRemoteRings(in: store)
        let fractions = remotes.compactMap(\.usedFraction)
        XCTAssertEqual(remotes.count, 2, "each remote connection keeps its own ring")
        XCTAssertEqual(fractions.count, 2)
        XCTAssertEqual(Set(fractions).count, 2, "quotas must not be summed or shared")
    }

    // SPECSFY: US-003 FR-002 FR-003 NFR-001 AC-010
    func testPhoneTapDistinguishesTwoRemoteConnectionNames() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [
                RemoteUsageConnection(assistantID: "claude", connectionName: "Office"),
                RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")
            ]
        )
        let names = phoneSnapshot(from: store).providers
            .filter { $0.id.hasPrefix("claude:") && $0.id != "claude" }
            .map(\.displayName)
        XCTAssertEqual(Set(names).count, 2, "each phone tap must reveal that connection's own name")
    }

    // SPECSFY: US-002 FR-004 NFR-003 AC-011
    func testExtraRingDoesNotRequireHerdrOrAMachineCatalog() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Office")]
        )
        XCTAssertNotNil(
            store.notchSnapshots.first(where: { $0.id == "claude:Office" }),
            "an extra ring must be able to appear without Herdr and without registering a machine"
        )
    }

    // SPECSFY: US-002 FR-004 NFR-003 AC-012
    func testAccountsSettingsOfferHerdrWithoutAMachineCatalog() {
        let name = "RemoteUsageTests.herdr.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        let preferences = Preferences(defaults: defaults)
        XCTAssertNotNil(
            defaults.object(forKey: "herdrEnabled"),
            "Accounts Settings must persist the optional Herdr switch, without a machine catalog"
        )
        XCTAssertFalse(preferences.herdrEnabled)
    }

    // SPECSFY: US-001 FR-001 FR-002 FR-003 NFR-002 AC-001 AC-004 AC-009
    func testNotchStripShowsTwoRemoteRingsWithTheAssistantGlyph() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [
                RemoteUsageConnection(assistantID: "claude", connectionName: "Office"),
                RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")
            ]
        )
        let model = NotchViewModel()
        model.updateSnapshots(store.notchSnapshots)
        let remotes = model.snapshots.filter { $0.id.hasPrefix("claude:") && $0.id != "claude" }

        XCTAssertEqual(remotes.count, 2, "the notch strip must keep one extra ring per remote connection")
        XCTAssertTrue(remotes.allSatisfy { $0.glyph == .claude })
        XCTAssertTrue(remotes.allSatisfy(\.isRemoteExtraReading))

        model.sessions["claude"] = [
            AgentSession(id: "local-session", name: "local", detail: "Claude",
                         state: .busy, waitingFor: nil, since: Date())
        ]
        XCTAssertNil(
            model.activity(for: remotes[0]),
            "an extra remote ring must not borrow the assistant's local session"
        )
    }

    // SPECSFY: US-001 FR-001 NFR-002 AC-001
    func testNotchStripDropsRemoteRingsWhenTheAssistantIsOff() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let connections = [
            RemoteUsageConnection(assistantID: "claude", connectionName: "Office")
        ]
        let model = NotchViewModel()
        model.updateSnapshots(makeStore([assistant], remoteConnections: connections).notchSnapshots)
        XCTAssertTrue(model.snapshots.contains { $0.id == "claude:Office" })

        model.updateSnapshots(
            makeStore([assistant], disconnected: ["claude"], remoteConnections: connections).notchSnapshots
        )
        XCTAssertFalse(
            model.snapshots.contains { $0.id == "claude:Office" },
            "turning the assistant off must drop the extra ring from the notch strip"
        )
    }

    // SPECSFY: US-001 FR-002 NFR-002 AC-004 AC-009
    func testTooltipCopyNamesEachRemoteConnectionOffTheRing() {
        let assistant = RemoteUsageProbe(id: "claude", connectionName: "local")
        let store = makeStore(
            [assistant],
            remoteConnections: [
                RemoteUsageConnection(assistantID: "claude", connectionName: "Office"),
                RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")
            ]
        )
        let remotes = extraRemoteRings(in: store)
        XCTAssertEqual(Set(remotes.compactMap(\.remoteConnectionName)), ["Office", "Lab"])
        XCTAssertFalse(remotes.contains { $0.displayName == "Office" || $0.displayName == "Lab" })
        XCTAssertEqual(
            store.notchSnapshots.first { $0.id == "claude" }?.remoteConnectionName,
            nil,
            "the local assistant ring has no connection name on the tooltip"
        )
    }

    func testSSHPassesRemoteScriptAsASingleArgument() {
        let command = HerdrRemoteUsageProbe.remoteAgentListScript
        let args = HerdrRemoteUsageProbe.sshArguments(target: "lab", command: command)
        XCTAssertEqual(args.last, command)
        XCTAssertEqual(args.filter { $0 == "lab" }.count, 1)
        XCTAssertFalse(args.contains("bash"))
        XCTAssertFalse(args.contains("-s"))
        XCTAssertFalse(args.contains("-c"))
    }

    func testHerdrAgentListDrivesRemoteRingsNotLocalProfiles() {
        let machines = """
        [{"id":"a","label":"Office","target":"office","session":"default","enabled":true,"selected":false},
         {"id":"b","label":"Lab","target":"lab","session":"default","enabled":true,"selected":false},
         {"id":"c","label":"Idle","target":"idle","session":"default","enabled":true,"selected":false}]
        """.data(using: .utf8)!
        let officeAgents = """
        {"id":"cli:agent:list","result":{"agents":[{"agent":"codex"},{"agent":"codex"}],"type":"agent_list"}}
        """.data(using: .utf8)!
        let labAgents = """
        {"id":"cli:agent:list","result":{"agents":[{"agent":"claude"},{"agent":"claude"}],"type":"agent_list"}}
        """.data(using: .utf8)!
        let emptyAgents = """
        {"id":"cli:agent:list","result":{"agents":[],"type":"agent_list"}}
        """.data(using: .utf8)!
        let probe = HerdrRemoteUsageProbe(
            listMachines: { machines },
            listAgents: { target in
                switch target {
                case "office": return officeAgents
                case "lab": return labAgents
                default: return emptyAgents
                }
            },
            readUsage: { _ in throw UsageProviderError.badResponse(status: 0) }
        )
        XCTAssertEqual(
            Set(probe.liveConnections().map(\.id)),
            ["codex:Office", "claude:Lab"]
        )
    }

    func testRemoteExtraFollowsAnyClaudeProfileNotOnlyTheDefault() {
        let workProfile = RemoteUsageProbe(id: "claude-work", connectionName: "local")
        let store = makeStore(
            [workProfile],
            disconnected: ["claude"],
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")]
        )
        XCTAssertNotNil(
            store.notchSnapshots.first { $0.id == "claude:Lab" },
            "a remote Claude ring must stay when another Claude profile is still on"
        )
    }

    func testHerdrUsageReadingFillsTheExtraRing() async {
        let usage = """
        You are currently using your subscription to power your Claude Code usage

        Current session: 22% used
        Current week (all models): 10% used · resets Sep 23, 11pm (Europe/Berlin)
        """
        let machines = """
        [{"id":"a","label":"Build","target":"build","session":"default","enabled":true,"selected":false}]
        """.data(using: .utf8)!
        let agents = """
        {"id":"cli:agent:list","result":{"agents":[{"agent":"claude"}],"type":"agent_list"}}
        """.data(using: .utf8)!
        let probe = HerdrRemoteUsageProbe(
            listMachines: { machines },
            listAgents: { _ in agents },
            readUsage: { target in
                XCTAssertEqual(target, "build")
                return usage
            }
        )
        let assistant = RemoteUsageProbe(id: "claude-work", connectionName: "local")
        let store = makeStore([assistant], disconnected: ["claude"])
        store.applyRemoteReadings(connections: probe.liveConnections())
        XCTAssertFalse(
            extraRemoteRings(in: store).first?.hasReading ?? true,
            "the extra ring starts empty until SSH usage lands"
        )
        let readings = await probe.readEnabled()
        store.applyRemoteReadings(connections: probe.liveConnections(), successes: readings)
        guard let extra = extraRemoteRings(in: store).first else {
            XCTFail("the extra ring should remain after a good Herdr reading")
            return
        }
        XCTAssertEqual(extra.remoteConnectionName, "Build")
        XCTAssertEqual(extra.usedFraction, 0.22)
        XCTAssertFalse(extra.status.isStale)
    }

    func testRemoteExtraUsesFamilyNameNotLocalProfileSlug() {
        let workProfile = RemoteUsageProbe(id: "claude-work", connectionName: "work")
        let store = makeStore(
            [workProfile],
            disconnected: ["claude"],
            remoteConnections: [RemoteUsageConnection(assistantID: "claude", connectionName: "Office")]
        )
        guard let extra = store.notchSnapshots.first(where: { $0.id == "claude:Office" }) else {
            XCTFail("the extra ring should use the Claude family, not a local profile slug")
            return
        }
        XCTAssertEqual(extra.displayName, "Claude")
        XCTAssertEqual(extra.usageCardTitle, L10n.t("Claude Usage"))
        XCTAssertEqual(extra.remoteConnectionName, "Office")
        XCTAssertFalse(extra.displayName.contains("work"))
    }

    func testSettingsListsRemoteExtrasAndCanHideOne() {
        let workProfile = RemoteUsageProbe(id: "claude-work", connectionName: "work")
        let store = makeStore(
            [workProfile],
            disconnected: ["claude:Office"],
            remoteConnections: [
                RemoteUsageConnection(assistantID: "claude", connectionName: "Office"),
                RemoteUsageConnection(assistantID: "claude", connectionName: "Lab")
            ]
        )
        XCTAssertNil(store.notchSnapshots.first { $0.id == "claude:Office" })
        XCTAssertNotNil(store.notchSnapshots.first { $0.id == "claude:Lab" })
        XCTAssertEqual(
            Set(store.remoteAccountSummaries.map(\.id)),
            ["claude:Office", "claude:Lab"]
        )
        XCTAssertEqual(
            store.remoteAccountSummaries.first { $0.id == "claude:Office" }?.name,
            "Claude · Office"
        )
    }

    func testRemoteExtraDefaultsOnUntilSettingsHidesIt() {
        let name = "RemoteUsageTests.remoteOn.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        defaults.set(["claude"], forKey: "connectedProviders")
        let preferences = Preferences(defaults: defaults)
        XCTAssertTrue(preferences.isConnected("claude:Office"))
        preferences.setConnected(false, for: "claude:Office")
        XCTAssertFalse(preferences.isConnected("claude:Office"))
        preferences.setConnected(true, for: "claude:Office")
        XCTAssertTrue(preferences.isConnected("claude:Office"))
    }
}

/// Same glyph as the assistant, distinct identity for the remote connection.
private final class RemoteUsageProbe: UsageProvider, @unchecked Sendable {
    let id: String
    let displayName: String
    let glyph = ProviderGlyph.claude

    init(id: String, connectionName: String) {
        self.id = id
        self.displayName = connectionName
    }

    func fetchSnapshot() async throws -> ProviderSnapshot {
        ProviderSnapshot(
            id: id, displayName: displayName, glyph: glyph,
            fidelity: .official, status: .ok,
            windows: [LimitWindow(id: "session", label: "Session", usedFraction: 0.42)]
        )
    }

    func account() -> ProviderAccount? {
        ProviderAccount(label: displayName, plan: nil, source: "RemoteUsageProbe", manageURL: nil)
    }

    nonisolated var signInRoute: SignInRoute { .guidance("") }
    func signOut() async {}
    func presentSignIn() {}
    nonisolated func forgetCachedCredential() {}
}
