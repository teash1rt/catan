import { z } from "zod";

// 共享 schema 必须兼容 Electron 生产环境禁止 eval 的严格 CSP。
z.config({ jitless: true });

export const terrainSchema = z.enum(["forest", "brick", "stone", "wheat", "sheep", "desert"]);
export const harborKindSchema = z.enum(["generic", "lumber", "brick", "ore", "grain", "wool"]);
export const mapConfigSchema = z.object({
  seed: z.number().int().min(0).max(0xffffffff),
  tiles: z
    .array(
      z.object({
        id: z.string().min(1),
        q: z.number().int(),
        r: z.number().int(),
        terrain: terrainSchema,
        number: z
          .number()
          .int()
          .min(2)
          .max(12)
          .refine((n) => n !== 7)
          .nullable(),
      }),
    )
    .min(1)
    .max(256),
  harbors: z.array(z.object({ edgeId: z.string().min(1), kind: harborKindSchema })).max(128),
  robberTileId: z.string().min(1),
});
export type Terrain = z.infer<typeof terrainSchema>;
export type HarborKind = z.infer<typeof harborKindSchema>;
export type MapConfig = z.infer<typeof mapConfigSchema>;
