import { describe, expect, it } from "vitest";
import { sessionMatchesAgenda } from "./scheduleService";

const block = (meetingId: string, agendaItems: string[]) => ({ meetingId, agendaItems }) as never;

describe("RAN2 parent blocks", () => {
  it("a RAN2 block marked 8.2 shows for a followed 8.2.4", () => {
    expect(sessionMatchesAgenda(block("ran2-136", ["8.2"]), ["8.2.4"])).toBe(true);
  });
  it("a RAN1 block marked 10.8 shows for a followed 10.8.1", () => {
    expect(sessionMatchesAgenda(block("ran1-127", ["10.8"]), ["10.8.1"])).toBe(true);
    expect(sessionMatchesAgenda(block("ran1-127", ["10.8.2"]), ["10.8.1"])).toBe(false);
    expect(sessionMatchesAgenda(block("ran1-127", ["10.4.x"]), ["10.4.1"])).toBe(true);
  });
});
