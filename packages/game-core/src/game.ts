import {
  createGameInputSchema,
  gameCommandSchema,
  gameStateSchema,
  resourceSchema,
} from "@catan/protocol";
import type {
  GameCommand,
  GameCommandResult,
  GameError,
  GameEvent,
  GamePhase,
  GameState,
  LegalPlacements,
  Resource,
  ResourceCounts,
  Terrain,
} from "@catan/protocol";
import { buildTopology, validateMapConfig } from "./map.ts";
import type { Topology } from "./map.ts";

// 基础版每人放置两组村庄与道路，每类资源总计 19 张。
const CLASSIC_SETUP_RULES = { rounds: 2, bankPerResource: 19 } as const;
const TERRAIN_RESOURCE: Record<Terrain, Resource | null> = {
  forest: "lumber",
  brick: "brick",
  stone: "ore",
  wheat: "grain",
  sheep: "wool",
  desert: null,
};

function resourceCounts(count: number): ResourceCounts {
  return { lumber: count, brick: count, ore: count, grain: count, wool: count };
}

/** 玩家数组即先手开始的行动顺序；随机地图与玩家排序均由调用方负责。 */
export function createGame(input: unknown): GameState {
  const { map, players, rules } = createGameInputSchema.parse(input);
  return {
    map: validateMapConfig(map),
    rules,
    players: players.map((player) => ({ ...player, resources: resourceCounts(0) })),
    settlements: [],
    roads: [],
    bank: resourceCounts(CLASSIC_SETUP_RULES.bankPerResource),
    phase: { type: "initial-settlement", playerId: players[0]!.id, round: 1 },
  };
}

type GameContext = { state: GameState; topology: Topology };

function readGame(input: GameState): GameContext {
  // Zod 在包边界校验并复制数据，后续修改只作用于本次转换持有的副本。
  const state = gameStateSchema.parse(input);
  validateMapConfig(state.map);
  const topology = buildTopology(state.map.tiles);
  const validVertices = new Set(topology.vertices.map((vertex) => vertex.id));
  const validEdges = new Set(topology.edges.map((edge) => edge.id));
  if (
    state.settlements.some((piece) => !validVertices.has(piece.vertexId)) ||
    state.roads.some((piece) => !validEdges.has(piece.edgeId)) ||
    resourceSchema.options.some(
      (resource) =>
        state.bank[resource] +
          state.players.reduce((total, player) => total + player.resources[resource], 0) !==
        CLASSIC_SETUP_RULES.bankPerResource,
    )
  ) {
    throw new Error("建筑引用或资源总量无效");
  }
  const phase = state.phase;
  if (
    phase.type === "initial-road" &&
    !state.settlements.some(
      (piece) => piece.vertexId === phase.vertexId && piece.playerId === phase.playerId,
    )
  ) {
    throw new Error("道路阶段未引用当前玩家的村庄");
  }
  return { state, topology };
}

function placementError(
  { state, topology }: GameContext,
  command: GameCommand,
): GameError | undefined {
  if (command.type === "place-initial-settlement") {
    if (state.phase.type !== "initial-settlement") {
      return "WRONG_PHASE";
    }
    if (!topology.vertices.some((vertex) => vertex.id === command.vertexId)) {
      return "UNKNOWN_VERTEX";
    }
    const occupied = new Set(state.settlements.map((piece) => piece.vertexId));
    if (occupied.has(command.vertexId)) {
      return "OCCUPIED";
    }
    if (
      topology.edges.some(
        (edge) =>
          (edge.a === command.vertexId && occupied.has(edge.b)) ||
          (edge.b === command.vertexId && occupied.has(edge.a)),
      )
    ) {
      return "DISTANCE_RULE";
    }
    return undefined;
  }

  if (state.phase.type !== "initial-road") {
    return "WRONG_PHASE";
  }
  const edge = topology.edges.find((candidate) => candidate.id === command.edgeId);
  if (!edge) {
    return "UNKNOWN_EDGE";
  }
  if (state.roads.some((piece) => piece.edgeId === command.edgeId)) {
    return "OCCUPIED";
  }
  if (edge.a !== state.phase.vertexId && edge.b !== state.phase.vertexId) {
    return "ROAD_NOT_ADJACENT";
  }
  return undefined;
}

function startingResources({ state, topology }: GameContext, vertexId: string): ResourceCounts {
  const resources = resourceCounts(0);
  const vertex = topology.vertices.find((candidate) => candidate.id === vertexId)!;
  for (const tile of state.map.tiles) {
    const resource = TERRAIN_RESOURCE[tile.terrain];
    if (resource !== null && vertex.tileIds.includes(tile.id)) {
      resources[resource]++;
    }
  }
  return resources;
}

function nextPhase(
  state: GameState,
  phase: Extract<GamePhase, { type: "initial-road" }>,
): GamePhase {
  const playerIndex = state.players.findIndex((player) => player.id === phase.playerId);
  if (phase.round === 1) {
    const nextPlayer = state.players[playerIndex + 1];
    return {
      type: "initial-settlement",
      playerId: nextPlayer?.id ?? phase.playerId,
      round: nextPlayer ? 1 : CLASSIC_SETUP_RULES.rounds,
    };
  }
  const nextPlayer = state.players[playerIndex - 1];
  return nextPlayer
    ? { type: "initial-settlement", playerId: nextPlayer.id, round: phase.round }
    : { type: "awaiting-roll", playerId: state.players[0]!.id };
}

/** 身份由宿主提供；本函数不信任命令中自行声明的玩家或建筑归属。 */
export function applyGameCommand(
  input: GameState,
  actorId: string,
  commandInput: unknown,
): GameCommandResult {
  const parsed = gameCommandSchema.safeParse(commandInput);
  if (!parsed.success) {
    return { ok: false, error: "INVALID_COMMAND" };
  }
  let context: GameContext;
  try {
    context = readGame(input);
  } catch {
    return { ok: false, error: "INVALID_STATE" };
  }
  const { state } = context;
  if (!state.players.some((player) => player.id === actorId)) {
    return { ok: false, error: "UNKNOWN_PLAYER" };
  }
  if (state.phase.playerId !== actorId) {
    return { ok: false, error: "NOT_YOUR_TURN" };
  }
  const command = parsed.data;
  const error = placementError(context, command);
  if (error) {
    return { ok: false, error };
  }

  const events: GameEvent[] = [];
  const phase = state.phase;
  if (command.type === "place-initial-settlement" && phase.type === "initial-settlement") {
    if (phase.round === CLASSIC_SETUP_RULES.rounds) {
      const resources = startingResources(context, command.vertexId);
      if (resourceSchema.options.some((resource) => state.bank[resource] < resources[resource])) {
        return { ok: false, error: "INVALID_STATE" };
      }
      const player = state.players.find((candidate) => candidate.id === actorId)!;
      for (const resource of resourceSchema.options) {
        player.resources[resource] += resources[resource];
        state.bank[resource] -= resources[resource];
      }
      events.push({ type: "starting-resources-granted", playerId: actorId, resources });
    }
    state.settlements.push({ vertexId: command.vertexId, playerId: actorId });
    state.phase = {
      type: "initial-road",
      playerId: actorId,
      round: phase.round,
      vertexId: command.vertexId,
    };
    // 事件按因果排序：先落下村庄，再发放该村庄带来的起始资源。
    events.unshift({ type: "settlement-placed", playerId: actorId, vertexId: command.vertexId });
  } else if (command.type === "place-initial-road" && phase.type === "initial-road") {
    state.roads.push({ edgeId: command.edgeId, playerId: actorId });
    state.phase = nextPhase(state, phase);
    events.push({ type: "road-placed", playerId: actorId, edgeId: command.edgeId });
    if (state.phase.type === "awaiting-roll") {
      events.push({ type: "setup-completed", playerId: state.phase.playerId });
    }
  }
  return { ok: true, state, events };
}

/** 仅列出当前阶段可提交的位置；未来界面无需另写一套建造规则。 */
export function getLegalPlacements(input: GameState): LegalPlacements {
  const context = readGame(input);
  return {
    settlementVertexIds: context.topology.vertices
      .filter(
        (vertex) =>
          !placementError(context, { type: "place-initial-settlement", vertexId: vertex.id }),
      )
      .map((vertex) => vertex.id),
    roadEdgeIds: context.topology.edges
      .filter((edge) => !placementError(context, { type: "place-initial-road", edgeId: edge.id }))
      .map((edge) => edge.id),
  };
}
