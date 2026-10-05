import { describe, expect, it } from "vitest";
import type { ZodType } from "zod";
import fixtures from "./contract/fixtures/fixtures.json";
import * as schemas from "./contract/panel.gen";

const schemaByName = schemas as unknown as Record<string, ZodType>;

describe("generated contract fixtures", () => {
  it("parses every fixture through its generated schema", () => {
    for (const [name, fixture] of Object.entries(fixtures)) {
      const schema = schemaByName[name];

      expect(schema, `no generated schema named ${name}`).toBeDefined();
      expect(
        schema!.safeParse(fixture).success,
        `${name} fixture does not parse through its schema`,
      ).toBe(true);
    }
  });
});
