import { describe, expect, it } from "@effect/vitest";
import * as Effect from "effect/Effect";
import * as EffectAcpErrors from "effect-acp/errors";

import {
  applyHermesAcpModelSelection,
  buildHermesAcpSpawnInput,
  resolveHermesAcpBaseModelId,
} from "./HermesAcpSupport.ts";

describe("resolveHermesAcpBaseModelId", () => {
  it("preserves exact ACP model ids and defaults to Sol", () => {
    expect(resolveHermesAcpBaseModelId(undefined)).toBe("openai-codex:gpt-5.6-sol");
    expect(resolveHermesAcpBaseModelId("   ")).toBe("openai-codex:gpt-5.6-sol");
    expect(resolveHermesAcpBaseModelId("  openai-codex:gpt-5.6-terra  ")).toBe(
      "openai-codex:gpt-5.6-terra",
    );
  });
});

describe("buildHermesAcpSpawnInput", () => {
  it("uses fixed stdio command and allowlists the Hermes environment", () => {
    const spawn = buildHermesAcpSpawnInput({ enabled: true }, "/tmp/project", {
      HERMES_HOME: "/state/hermes",
      DEVPASS_API_KEY: "secret",
      UNTRUSTED_BROWSER_VALUE: "blocked",
    });

    expect(spawn).toEqual({
      command: "/usr/local/bin/hermes",
      args: ["acp"],
      cwd: "/tmp/project",
      env: {
        HERMES_HOME: "/state/hermes",
        DEVPASS_API_KEY: "secret",
      },
    });
  });
});

describe("applyHermesAcpModelSelection", () => {
  const makeRecordingRuntime = (failure?: EffectAcpErrors.AcpError) => {
    const modelCalls: Array<string> = [];
    const runtime = {
      setSessionModel: (modelId: string) =>
        Effect.gen(function* () {
          modelCalls.push(modelId);
          if (failure) return yield* failure;
          return {};
        }),
    };
    return { runtime, modelCalls };
  };

  it.effect("calls session/set_model when the requested model differs from current", () =>
    Effect.gen(function* () {
      const { runtime, modelCalls } = makeRecordingRuntime();
      const result = yield* applyHermesAcpModelSelection({
        runtime,
        currentModelId: "openai-codex:gpt-5.6-sol",
        requestedModelId: "openai-codex:gpt-5.6-terra",
        mapError: (cause) => cause.message,
      });
      expect(modelCalls).toEqual(["openai-codex:gpt-5.6-terra"]);
      expect(result).toBe("openai-codex:gpt-5.6-terra");
    }),
  );

  it.effect("skips set_model when requested matches current", () =>
    Effect.gen(function* () {
      const { runtime, modelCalls } = makeRecordingRuntime();
      const result = yield* applyHermesAcpModelSelection({
        runtime,
        currentModelId: "openai-codex:gpt-5.6-sol",
        requestedModelId: "openai-codex:gpt-5.6-sol",
        mapError: (cause) => cause.message,
      });
      expect(modelCalls).toEqual([]);
      expect(result).toBe("openai-codex:gpt-5.6-sol");
    }),
  );

  it.effect("skips set_model when no model is requested", () =>
    Effect.gen(function* () {
      const { runtime, modelCalls } = makeRecordingRuntime();
      const result = yield* applyHermesAcpModelSelection({
        runtime,
        currentModelId: "openai-codex:gpt-5.6-sol",
        requestedModelId: undefined,
        mapError: (cause) => cause.message,
      });
      expect(modelCalls).toEqual([]);
      expect(result).toBe("openai-codex:gpt-5.6-sol");
    }),
  );

  it.effect("propagates session/set_model failures via mapError", () =>
    Effect.gen(function* () {
      const failure = EffectAcpErrors.AcpRequestError.invalidParams("session id not known");
      const { runtime } = makeRecordingRuntime(failure);
      const error = yield* Effect.flip(
        applyHermesAcpModelSelection({
          runtime,
          currentModelId: "openai-codex:gpt-5.6-sol",
          requestedModelId: "openai-codex:gpt-5.6-terra",
          mapError: (cause) => cause.message,
        }),
      );
      expect(error).toBe(failure.message);
    }),
  );
});
