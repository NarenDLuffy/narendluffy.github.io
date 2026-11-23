import { describe, expect, it } from "vitest";
import { parseDraftName } from "./draftThreads";

describe("parseDraftName", () => {
  it("takes the last company after the version as the uploader", () => {
    const p = parseDraftName("UL PAPR reduction results - V4.10-ETRI_IDC.xlsx");
    expect(p.version).toEqual([4, 10]);
    expect(p.author).toBe("IDC");
    expect(p.key).toBe("ul papr reduction results");
  });
  it("puts differently punctuated copies of one title in the same thread", () => {
    expect(parseDraftName("UL_PAPR_reduction_results - V4.2-Sony_MediaTek.xlsx").key).toBe(
      parseDraftName("UL PAPR reduction results - V4.3-MediaTek_HW.xlsx").key,
    );
  });
});
