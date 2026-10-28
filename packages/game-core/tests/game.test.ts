import assert from "node:assert/strict";
import test from "node:test";
import {
  applyGameCommand,
  buildTopology,
  createClassicMap,
  createGame,
  getLegalPlacements,
} from "@catan/game-core";
import {
  createGameInputSchema,
  gameCommandResultSchema,
  gameCommandSchema,
  gameEventSchema,
  gameStateSchema,
  legalPlacementsSchema,
  resourceSchema,
  ruleConfigSchema,
} from "@catan/protocol";
import type { GameCommand, GameEvent, GameError, GameState, ResourceCounts } from "@catan/protocol";

const PLAYER_IDS = ["A", "B", "C", "D"];
const EMPTY_RESOURCES: ResourceCounts = { lumber: 0, brick: 0, ore: 0, grain: 0, wool: 0 };
const FULL_BANK: ResourceCounts = { lumber: 19, brick: 19, ore: 19, grain: 19, wool: 19 };

function input(playerCount = 4, seed = 42) {
  return {
    map: createClassicMap(seed),
    players: PLAYER_IDS.slice(0, playerCount).map((id) => ({ id })),
    rules: { preset: "classic" as const },
  };
}

function freeze(value: unknown): void {
  if (value !== null && typeof value === "object") {
    Object.freeze(value);
    for (const child of Object.values(value)) {
      freeze(child);
    }
  }
}

function execute(state: GameState, command: GameCommand, actorId = state.phase.playerId) {
  const before = structuredClone(state);
  freeze(state);
  const result = applyGameCommand(state, actorId, command);
  assert.deepEqual(state, before);
  assert.ok(result.ok, JSON.stringify(result));
  assert.notEqual(result.state, state);
  assert.deepEqual(gameCommandResultSchema.parse(result), result);
  return result;
}

function reject(
  state: GameState,
  command: unknown,
  error: GameError,
  actorId = state.phase.playerId,
) {
  const before = structuredClone(state);
  freeze(state);
  const result = applyGameCommand(state, actorId, command);
  assert.deepEqual(result, { ok: false, error });
  assert.deepEqual(state, before);
  assert.deepEqual(gameCommandResultSchema.parse(result), result);
}

function playSetup(playerCount: number, seed = 42, playerIds = PLAYER_IDS) {
  let state = createGame({
    ...input(playerCount, seed),
    players: playerIds.slice(0, playerCount).map((id) => ({ id })),
  });
  const states = [state];
  const events: GameEvent[] = [];
  const order: string[] = [];
  while (state.phase.type !== "awaiting-roll") {
    const legal = getLegalPlacements(state);
    const command: GameCommand =
      state.phase.type === "initial-settlement"
        ? { type: "place-initial-settlement", vertexId: legal.settlementVertexIds.at(0)! }
        : { type: "place-initial-road", edgeId: legal.roadEdgeIds.at(0)! };
    if (command.type === "place-initial-settlement") {
      order.push(state.phase.playerId);
    }
    const result = execute(state, command);
    state = result.state;
    events.push(...result.events);
    states.push(state);
  }
  return { state, states, events, order };
}

void test("initialization validates boundaries, copies inputs and starts with an empty board", () => {
  const options = input();
  const before = structuredClone(options);
  freeze(options);
  const state = createGame(options);
  assert.deepEqual(options, before);
  assert.deepEqual(state.phase, { type: "initial-settlement", playerId: "A", round: 1 });
  assert.deepEqual(state.settlements, []);
  assert.deepEqual(state.roads, []);
  assert.deepEqual(state.bank, FULL_BANK);
  assert.deepEqual(
    state.players.map((player) => player.resources),
    PLAYER_IDS.map(() => EMPTY_RESOURCES),
  );
  assert.notEqual(state.map, options.map);
  assert.notEqual(state.players.at(0)!.resources, state.players.at(1)!.resources);
  assert.deepEqual(gameStateSchema.parse(state), state);

  for (const playerCount of [2, 5]) {
    const invalid = {
      ...input(),
      players: Array.from({ length: playerCount }, (_, index) => ({ id: `${index}` })),
    };
    assert.throws(() => createGame(invalid));
  }
  assert.throws(() => createGame({ ...input(), players: [{ id: "A" }, { id: "B" }, { id: "A" }] }));
  assert.throws(() => createGame({ ...input(), players: [{ id: "" }, { id: "B" }, { id: "C" }] }));
  assert.throws(() => createGame({ ...input(), rules: { preset: "custom" } }));
  assert.throws(() => createGame({ ...input(), map: { ...options.map, robberTileId: "missing" } }));
  assert.equal(createGameInputSchema.safeParse(null).success, false);
  assert.equal(ruleConfigSchema.safeParse({ preset: "classic", rounds: 3 }).success, false);
});

for (const playerCount of [3, 4]) {
  void test(`${playerCount} players complete both snake rounds and stop before the first roll`, () => {
    const { state, states, events, order } = playSetup(playerCount);
    const players = PLAYER_IDS.slice(0, playerCount);
    assert.deepEqual(order, [...players, ...players.toReversed()]);
    assert.deepEqual(state.phase, { type: "awaiting-roll", playerId: "A" });
    assert.equal(state.settlements.length, playerCount * 2);
    assert.equal(state.roads.length, playerCount * 2);
    assert.equal(new Set(state.settlements.map((piece) => piece.vertexId)).size, playerCount * 2);
    assert.equal(new Set(state.roads.map((piece) => piece.edgeId)).size, playerCount * 2);

    const topology = buildTopology(state.map.tiles);
    for (const player of players) {
      assert.equal(state.settlements.filter((piece) => piece.playerId === player).length, 2);
      assert.equal(state.roads.filter((piece) => piece.playerId === player).length, 2);
      const grants = events.filter(
        (event) => event.type === "starting-resources-granted" && event.playerId === player,
      );
      assert.equal(grants.length, 1);
    }
    for (const edge of topology.edges) {
      assert.ok(
        !state.settlements.some((piece) => piece.vertexId === edge.a) ||
          !state.settlements.some((piece) => piece.vertexId === edge.b),
      );
    }
    for (const [index, snapshot] of states.entries()) {
      for (const resource of resourceSchema.options) {
        assert.equal(
          snapshot.bank[resource] +
            snapshot.players.reduce((sum, player) => sum + player.resources[resource], 0),
          19,
        );
      }
      if (snapshot.phase.type === "initial-road") {
        const beforeRoad = snapshot.phase;
        const afterRoad = states.at(index + 1)!;
        const road = topology.edges.find((edge) => edge.id === afterRoad.roads.at(-1)!.edgeId)!;
        assert.ok(road.a === beforeRoad.vertexId || road.b === beforeRoad.vertexId);
      }
    }
    assert.deepEqual(
      events.slice(-2).map((event) => event.type),
      ["road-placed", "setup-completed"],
    );
    assert.equal(events.filter((event) => event.type === "setup-completed").length, 1);
    assert.deepEqual(getLegalPlacements(state), { settlementVertexIds: [], roadEdgeIds: [] });
    reject(state, { type: "place-initial-settlement", vertexId: "-4,0" }, "WRONG_PHASE");
    reject(state, { type: "place-initial-road", edgeId: topology.edges.at(0)!.id }, "WRONG_PHASE");
    reject(state, { type: "roll-dice" }, "INVALID_COMMAND");
  });
}

void test("caller-supplied player order determines both setup rounds and the first turn", () => {
  const players = ["third", "first", "second"];
  const { state, order } = playSetup(3, 42, players);
  assert.deepEqual(order, [...players, ...players.toReversed()]);
  assert.deepEqual(state.phase, { type: "awaiting-roll", playerId: "third" });
});

void test("identity and command boundaries reject spoofed ownership and malformed commands", () => {
  const state = createGame(input());
  const command: GameCommand = { type: "place-initial-settlement", vertexId: "-4,0" };
  for (const invalid of [
    null,
    [],
    {},
    { type: "undo" },
    { ...command, vertexId: "" },
    { ...command, vertexId: 1 },
    { ...command, playerId: "B" },
  ]) {
    reject(state, invalid, "INVALID_COMMAND");
    assert.equal(gameCommandSchema.safeParse(invalid).success, false);
  }
  reject(state, command, "UNKNOWN_PLAYER", "missing");
  reject(state, command, "NOT_YOUR_TURN", "B");
  const result = execute(state, command);
  assert.equal(result.state.settlements.at(0)!.playerId, "A");
  reject(result.state, command, "WRONG_PHASE");
});

void test("placements reject wrong phases, unknown slots, occupied slots, distance and disconnected roads", () => {
  const state = createGame(input());
  const topology = buildTopology(state.map.tiles);
  const firstVertex = topology.vertices.at(0)!.id;
  const adjacentEdge = topology.edges.find(
    (edge) => edge.a === firstVertex || edge.b === firstVertex,
  )!;
  const adjacentVertex = adjacentEdge.a === firstVertex ? adjacentEdge.b : adjacentEdge.a;
  reject(state, { type: "place-initial-road", edgeId: adjacentEdge.id }, "WRONG_PHASE");
  reject(state, { type: "place-initial-settlement", vertexId: "missing" }, "UNKNOWN_VERTEX");
  const roadState = execute(state, {
    type: "place-initial-settlement",
    vertexId: firstVertex,
  }).state;
  reject(roadState, { type: "place-initial-road", edgeId: "missing" }, "UNKNOWN_EDGE");
  const disconnectedEdge = topology.edges.find(
    (edge) => edge.a !== firstVertex && edge.b !== firstVertex,
  )!;
  reject(
    roadState,
    { type: "place-initial-road", edgeId: disconnectedEdge.id },
    "ROAD_NOT_ADJACENT",
  );
  const secondPlayer = execute(roadState, {
    type: "place-initial-road",
    edgeId: adjacentEdge.id,
  }).state;
  reject(secondPlayer, { type: "place-initial-settlement", vertexId: firstVertex }, "OCCUPIED");
  reject(
    secondPlayer,
    { type: "place-initial-settlement", vertexId: adjacentVertex },
    "DISTANCE_RULE",
  );
  const nextVertex = getLegalPlacements(secondPlayer).settlementVertexIds.at(0)!;
  const secondRoad = execute(secondPlayer, {
    type: "place-initial-settlement",
    vertexId: nextVertex,
  }).state;
  reject(secondRoad, { type: "place-initial-road", edgeId: adjacentEdge.id }, "OCCUPIED");
});

function secondRoundAt(vertexId: string): GameState {
  let state = createGame(input());
  const topology = buildTopology(state.map.tiles);
  // 首轮保留目标及其邻居，确保资源样例的第二座村庄可合法落下。
  const reserved = new Set([vertexId]);
  for (const edge of topology.edges) {
    if (edge.a === vertexId) {
      reserved.add(edge.b);
    }
    if (edge.b === vertexId) {
      reserved.add(edge.a);
    }
  }
  while (state.phase.type !== "awaiting-roll" && state.phase.round === 1) {
    const legal = getLegalPlacements(state);
    state = execute(
      state,
      state.phase.type === "initial-settlement"
        ? {
            type: "place-initial-settlement",
            vertexId: legal.settlementVertexIds.find((id) => !reserved.has(id))!,
          }
        : { type: "place-initial-road", edgeId: legal.roadEdgeIds.at(0)! },
    ).state;
  }
  assert.deepEqual(state.phase, { type: "initial-settlement", playerId: "D", round: 2 });
  assert.ok(getLegalPlacements(state).settlementVertexIds.includes(vertexId));
  assert.deepEqual(state.bank, FULL_BANK);
  return state;
}

// 种子 42 的固定拓扑样例：重复森林、沙漠邻接、单地块海岸与纯沙漠海岸。
const RESOURCE_CASES: [string, ResourceCounts][] = [
  ["-4,0", { ...EMPTY_RESOURCES, lumber: 2, brick: 1 }],
  ["5,-1", { ...EMPTY_RESOURCES, ore: 2, wool: 1 }],
  ["1,3", { ...EMPTY_RESOURCES, ore: 1, grain: 2 }],
  ["-1,-3", { ...EMPTY_RESOURCES, wool: 2 }],
  ["-8,-2", { ...EMPTY_RESOURCES, wool: 1 }],
  ["-1,-5", EMPTY_RESOURCES],
];

for (const [vertexId, expected] of RESOURCE_CASES) {
  void test(`second settlement at ${vertexId} grants exact resources once and updates bank atomically`, () => {
    const state = secondRoundAt(vertexId);
    const result = execute(state, { type: "place-initial-settlement", vertexId });
    const player = result.state.players.find((candidate) => candidate.id === "D")!;
    assert.deepEqual(player.resources, expected);
    for (const resource of resourceSchema.options) {
      assert.equal(result.state.bank[resource], 19 - expected[resource]);
    }
    assert.deepEqual(result.events, [
      { type: "settlement-placed", playerId: "D", vertexId },
      { type: "starting-resources-granted", playerId: "D", resources: expected },
    ]);
    reject(result.state, { type: "place-initial-settlement", vertexId }, "WRONG_PHASE");
    const afterRoad = execute(result.state, {
      type: "place-initial-road",
      edgeId: getLegalPlacements(result.state).roadEdgeIds.at(0)!,
    });
    assert.deepEqual(afterRoad.state.players, result.state.players);
    assert.deepEqual(afterRoad.state.bank, result.state.bank);
    assert.deepEqual(
      afterRoad.events.map((event) => event.type),
      ["road-placed"],
    );
  });
}

void test("second road must connect to the new settlement rather than the player's first one", () => {
  const state = secondRoundAt("-4,0");
  const firstVillage = state.settlements.find((piece) => piece.playerId === "D")!;
  const roadState = execute(state, { type: "place-initial-settlement", vertexId: "-4,0" }).state;
  const oldVillageEdge = buildTopology(state.map.tiles).edges.find(
    (edge) =>
      (edge.a === firstVillage.vertexId || edge.b === firstVillage.vertexId) &&
      !state.roads.some((piece) => piece.edgeId === edge.id),
  )!;
  reject(roadState, { type: "place-initial-road", edgeId: oldVillageEdge.id }, "ROAD_NOT_ADJACENT");
});

void test("legal placements match command acceptance for every slot throughout a full setup", () => {
  const { states } = playSetup(4);
  for (const state of states) {
    const topology = buildTopology(state.map.tiles);
    const before = structuredClone(state);
    const legal = getLegalPlacements(state);
    assert.deepEqual(legalPlacementsSchema.parse(legal), legal);
    for (const vertex of topology.vertices) {
      const result = applyGameCommand(state, state.phase.playerId, {
        type: "place-initial-settlement",
        vertexId: vertex.id,
      });
      assert.equal(result.ok, legal.settlementVertexIds.includes(vertex.id));
    }
    for (const edge of topology.edges) {
      const result = applyGameCommand(state, state.phase.playerId, {
        type: "place-initial-road",
        edgeId: edge.id,
      });
      assert.equal(result.ok, legal.roadEdgeIds.includes(edge.id));
    }
    assert.deepEqual(state, before);
  }
});

void test("states, events and command results survive JSON round trips deterministically", () => {
  for (const seed of [0, 42, 123, 0xffffffff]) {
    const first = playSetup(4, seed);
    const second = playSetup(4, seed);
    assert.deepEqual(second, first);
    for (const state of first.states) {
      const restored = gameStateSchema.parse(JSON.parse(JSON.stringify(state)));
      assert.deepEqual(restored, state);
      assert.deepEqual(getLegalPlacements(restored), getLegalPlacements(state));
      if (state.phase.type !== "awaiting-roll") {
        const legal = getLegalPlacements(state);
        const command: GameCommand =
          state.phase.type === "initial-settlement"
            ? { type: "place-initial-settlement", vertexId: legal.settlementVertexIds.at(0)! }
            : { type: "place-initial-road", edgeId: legal.roadEdgeIds.at(0)! };
        assert.deepEqual(
          applyGameCommand(restored, restored.phase.playerId, command),
          applyGameCommand(state, state.phase.playerId, command),
        );
      }
    }
    for (const event of first.events) {
      assert.deepEqual(gameEventSchema.parse(JSON.parse(JSON.stringify(event))), event);
    }
  }
});

void test("state boundaries reject invalid resource counts, references and duplicate occupancy", () => {
  const state = createGame(input());
  const command = { type: "place-initial-settlement", vertexId: "-4,0" };
  const invalidStates: GameState[] = [
    { ...state, bank: { ...state.bank, lumber: -1 } },
    { ...state, bank: { ...state.bank, lumber: 1.5 } },
    { ...state, bank: { ...state.bank, lumber: 18 } },
    { ...state, settlements: [{ vertexId: "missing", playerId: "A" }] },
    { ...state, settlements: [{ vertexId: "-4,0", playerId: "missing" }] },
    { ...state, roads: [{ edgeId: "missing", playerId: "A" }] },
    { ...state, phase: { type: "initial-settlement", playerId: "missing", round: 1 } },
    { ...state, phase: { type: "initial-road", playerId: "A", round: 1, vertexId: "-4,0" } },
    {
      ...state,
      settlements: [
        { vertexId: "-4,0", playerId: "A" },
        { vertexId: "-4,0", playerId: "B" },
      ],
    },
  ];
  for (const invalid of invalidStates) {
    reject(invalid, command, "INVALID_STATE", "A");
    assert.throws(() => getLegalPlacements(invalid));
  }
  assert.equal(
    gameStateSchema.safeParse({ ...state, bank: { ...state.bank, wool: Number.NaN } }).success,
    false,
  );
  assert.equal(
    gameEventSchema.safeParse({
      type: "starting-resources-granted",
      playerId: "A",
      resources: { ...EMPTY_RESOURCES, lumber: -1 },
    }).success,
    false,
  );
});
