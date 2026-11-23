import { describe, expect, it } from "vitest";
import { topicFolderCode } from "./ran4Topics";

const topics = { "201": ["7.4.2", "7.4.3.2"], "101-A": ["8.2.1"] };

describe("RAN4 topic folders", () => {
  it("links a topic folder to the topic's first agenda item, not the meeting number", () => {
    expect(topicFolderCode("[121][201] NR_RRM_Ph6", topics)).toBe("7.4.2");
    expect(topicFolderCode("[121][101-A] 6G system parameter (part I)", topics)).toBe("8.2.1");
  });
  it("a topic without agenda items stays unlinked; other folders are not topic folders", () => {
    expect(topicFolderCode("[121][100] Main Session", topics)).toBeNull();
    expect(topicFolderCode("10.8 (ISAC)", topics)).toBeUndefined();
  });
});
