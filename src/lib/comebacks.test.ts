import { describe, expect, it } from "vitest";
import { comebacksFor, matchComebackFolder, type Comeback } from "./comebacks";

const rows: Comeback[] = [
  { name: "R19PSCellinfo", agendaCode: "9.1", status: "open", number: "2" },
  { name: "R20_SON&MDT_Intra-CULTM", agendaCode: "11.2.2", status: "open" },
  { name: "6GAIML1_Usecase", agendaCode: "10.5.1", status: "closed" },
  { name: "Rel20_AIoT", agendaCode: "14.4", status: "open" },
];

describe("RAN3 comeback folders", () => {
  it("links a numbered folder to its agenda item", () => {
    expect(matchComebackFolder("CB # 2_R19PSCellinfo", rows)?.agendaCode).toBe("9.1");
  });
  it("links when folder and notes disagree on the number", () => {
    expect(matchComebackFolder("CB # 17_R20_SON&MDT_Intra-CULTM", rows)?.agendaCode).toBe("11.2.2");
  });
  it("links an unnumbered folder whose name starts with digits", () => {
    expect(matchComebackFolder("CB # 6GAIML1_Usecase", rows)?.agendaCode).toBe("10.5.1");
  });
  it("ignores folders that are not comebacks", () => {
    expect(matchComebackFolder("SONMDT offline", rows)).toBeNull();
  });
  it("lists open comebacks before closed ones for followed items", () => {
    expect(comebacksFor(rows, ["10.5.1", "9.1"]).map((r) => r.status)).toEqual(["open", "closed"]);
  });
});
