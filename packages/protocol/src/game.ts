import { z } from "zod";
import { mapConfigSchema } from "./map.ts";

const idSchema = z.string().min(1);
const countSchema = z.number().int().nonnegative();
const MIN_PLAYERS = 3;
const MAX_PLAYERS = 4;

export const resourceSchema = z.enum(["lumber", "brick", "ore", "grain", "wool"]);
export const resourceCountsSchema = z.object({
  lumber: countSchema,
  brick: countSchema,
  ore: countSchema,
  grain: countSchema,
  wool: countSchema,
});
export const ruleConfigSchema = z.strictObject({ preset: z.literal("classic") });

const playerSchema = z.strictObject({ id: idSchema });
const playersSchema = z.array(playerSchema).min(MIN_PLAYERS).max(MAX_PLAYERS);
const uniquePlayers = (players: { id: string }[]): boolean =>
  new Set(players.map((player) => player.id)).size === players.length;

export const createGameInputSchema = z.strictObject({
  map: mapConfigSchema,
  players: playersSchema.refine(uniquePlayers, "玩家 ID 不能重复"),
  rules: ruleConfigSchema,
});

const setupPhase = { playerId: idSchema, round: z.union([z.literal(1), z.literal(2)]) };
export const gamePhaseSchema = z.discriminatedUnion("type", [
  z.strictObject({ type: z.literal("initial-settlement"), ...setupPhase }),
  z.strictObject({ type: z.literal("initial-road"), ...setupPhase, vertexId: idSchema }),
  z.strictObject({ type: z.literal("awaiting-roll"), playerId: idSchema }),
]);

export const gameStateSchema = z
  .strictObject({
    map: mapConfigSchema,
    rules: ruleConfigSchema,
    players: z
      .array(playerSchema.extend({ resources: resourceCountsSchema }))
      .min(MIN_PLAYERS)
      .max(MAX_PLAYERS)
      .refine(uniquePlayers, "玩家 ID 不能重复"),
    settlements: z.array(z.strictObject({ vertexId: idSchema, playerId: idSchema })),
    roads: z.array(z.strictObject({ edgeId: idSchema, playerId: idSchema })),
    bank: resourceCountsSchema,
    phase: gamePhaseSchema,
  })
  .refine((state) => {
    const players = new Set(state.players.map((player) => player.id));
    return (
      players.has(state.phase.playerId) &&
      state.settlements.every((piece) => players.has(piece.playerId)) &&
      state.roads.every((piece) => players.has(piece.playerId)) &&
      new Set(state.settlements.map((piece) => piece.vertexId)).size === state.settlements.length &&
      new Set(state.roads.map((piece) => piece.edgeId)).size === state.roads.length
    );
  }, "玩家引用或建筑位置无效");

export const gameCommandSchema = z.discriminatedUnion("type", [
  z.strictObject({ type: z.literal("place-initial-settlement"), vertexId: idSchema }),
  z.strictObject({ type: z.literal("place-initial-road"), edgeId: idSchema }),
]);

export const gameEventSchema = z.discriminatedUnion("type", [
  z.strictObject({ type: z.literal("settlement-placed"), playerId: idSchema, vertexId: idSchema }),
  z.strictObject({ type: z.literal("road-placed"), playerId: idSchema, edgeId: idSchema }),
  z.strictObject({
    type: z.literal("starting-resources-granted"),
    playerId: idSchema,
    resources: resourceCountsSchema,
  }),
  z.strictObject({ type: z.literal("setup-completed"), playerId: idSchema }),
]);

export const gameErrorSchema = z.enum([
  "INVALID_STATE",
  "INVALID_COMMAND",
  "UNKNOWN_PLAYER",
  "NOT_YOUR_TURN",
  "WRONG_PHASE",
  "UNKNOWN_VERTEX",
  "UNKNOWN_EDGE",
  "OCCUPIED",
  "DISTANCE_RULE",
  "ROAD_NOT_ADJACENT",
]);
export const gameCommandResultSchema = z.discriminatedUnion("ok", [
  z.strictObject({ ok: z.literal(true), state: gameStateSchema, events: z.array(gameEventSchema) }),
  z.strictObject({ ok: z.literal(false), error: gameErrorSchema }),
]);
export const legalPlacementsSchema = z.strictObject({
  settlementVertexIds: z.array(idSchema),
  roadEdgeIds: z.array(idSchema),
});

export type Resource = z.infer<typeof resourceSchema>;
export type ResourceCounts = z.infer<typeof resourceCountsSchema>;
export type RuleConfig = z.infer<typeof ruleConfigSchema>;
export type CreateGameInput = z.infer<typeof createGameInputSchema>;
export type GamePhase = z.infer<typeof gamePhaseSchema>;
export type GameState = z.infer<typeof gameStateSchema>;
export type GameCommand = z.infer<typeof gameCommandSchema>;
export type GameEvent = z.infer<typeof gameEventSchema>;
export type GameError = z.infer<typeof gameErrorSchema>;
export type GameCommandResult = z.infer<typeof gameCommandResultSchema>;
export type LegalPlacements = z.infer<typeof legalPlacementsSchema>;
