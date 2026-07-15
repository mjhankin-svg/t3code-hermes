import { describe, expect, it } from "@effect/vitest";
import * as Effect from "effect/Effect";
import * as Schema from "effect/Schema";
import { HermesSettings } from "@t3tools/contracts";

import { buildInitialHermesProviderSnapshot } from "./HermesProvider.ts";

const decodeHermesSettings = Schema.decodeSync(HermesSettings);

describe("buildInitialHermesProviderSnapshot", () => {
  it.effect("returns a disabled snapshot when settings.enabled is false", () =>
    Effect.gen(function* () {
      const snapshot = yield* buildInitialHermesProviderSnapshot(
        decodeHermesSettings({ enabled: false }),
      );
      expect(snapshot.enabled).toBe(false);
      expect(snapshot.status).toBe("disabled");
      expect(snapshot.installed).toBe(false);
      expect(snapshot.message).toContain("disabled");
    }),
  );

  it.effect("returns a pending snapshot by default", () =>
    Effect.gen(function* () {
      const snapshot = yield* buildInitialHermesProviderSnapshot(decodeHermesSettings({}));
      expect(snapshot.enabled).toBe(true);
      expect(snapshot.installed).toBe(true);
      expect(snapshot.status).toBe("warning");
      expect(snapshot.version).toBeNull();
      expect(snapshot.message).toContain("Checking Hermes");
      expect(snapshot.requiresNewThreadForModelChange).toBe(true);
    }),
  );
});
