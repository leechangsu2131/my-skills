import { describe, it, expect } from "vitest";
import { detectLessons, extractLessonContent, parseLessonStructure } from "./pdf-utils";

describe("PDF Utils", () => {
  describe("detectLessons", () => {
    it("should detect lessons with '차시' pattern", () => {
      const text = `
        차시 1: 덧셈의 기초
        내용...
        
        차시 2: 뺄셈의 기초
        내용...
      `;
      
      const lessons = detectLessons(text);
      expect(lessons).toHaveLength(2);
      expect(lessons[0].lessonNumber).toBe(1);
      expect(lessons[1].lessonNumber).toBe(2);
    });

    it("should detect lessons with '단원' pattern", () => {
      const text = `
        단원 1 - 수와 연산
        단원 2 - 도형
      `;
      
      const lessons = detectLessons(text);
      expect(lessons.length).toBeGreaterThan(0);
      expect(lessons[0].lessonNumber).toBe(1);
    });

    it("should handle lesson titles", () => {
      const text = "차시 1: 덧셈의 기초";
      const lessons = detectLessons(text);
      
      expect(lessons[0].title).toBe("덧셈의 기초");
    });

    it("should return empty array for text without lessons", () => {
      const text = "This is just some random text without lesson markers";
      const lessons = detectLessons(text);
      
      expect(lessons).toHaveLength(0);
    });
  });

  describe("extractLessonContent", () => {
    it("should extract content for specific lesson", () => {
      const text = `
        차시 1: 덧셈
        1 + 1 = 2
        
        차시 2: 뺄셈
        2 - 1 = 1
      `;
      
      const lessons = detectLessons(text);
      const content = extractLessonContent(text, 1, lessons);
      
      expect(content.content).toContain("1 + 1 = 2");
      expect(content.content).not.toContain("2 - 1 = 1");
    });

    it("should return empty content for non-existent lesson", () => {
      const text = "차시 1: 내용";
      const lessons = detectLessons(text);
      const content = extractLessonContent(text, 999, lessons);
      
      expect(content.content).toBe("");
    });

    it("should include lesson title in extracted content", () => {
      const text = "차시 1: 덧셈\n내용...";
      const lessons = detectLessons(text);
      const content = extractLessonContent(text, 1, lessons);
      
      expect(content.title).toBe("덧셈");
    });
  });

  describe("parseLessonStructure", () => {
    it("should parse lesson structure with previews", () => {
      const text = `
        차시 1: 덧셈
        이것은 덧셈에 대한 설명입니다. 덧셈은 두 수를 더하는 연산입니다.
        
        차시 2: 뺄셈
        이것은 뺄셈에 대한 설명입니다. 뺄셈은 두 수를 빼는 연산입니다.
      `;
      
      const lessons = detectLessons(text);
      const structure = parseLessonStructure(text, lessons);
      
      expect(structure).toHaveLength(2);
      expect(structure[0].lessonNumber).toBe(1);
      expect(structure[0].title).toBe("덧셈");
      expect(structure[0].preview).toBeTruthy();
      expect(structure[0].preview.length).toBeLessThanOrEqual(200);
    });

    it("should handle lessons without titles", () => {
      const text = `
        차시 1
        내용...
        
        차시 2
        내용...
      `;
      
      const lessons = detectLessons(text);
      const structure = parseLessonStructure(text, lessons);
      
      expect(structure).toHaveLength(2);
      expect(structure[0].lessonNumber).toBe(1);
    });
  });
});
