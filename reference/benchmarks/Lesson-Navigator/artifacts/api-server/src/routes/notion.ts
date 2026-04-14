import { Router, type IRouter } from "express";

const router: IRouter = Router();

router.get("/pages", async (req, res) => {
  try {
    const notionToken = process.env.NOTION_TOKEN;
    if (!notionToken) {
      res.json([]);
      return;
    }

    const { Client } = await import("@notionhq/client");
    const notion = new Client({ auth: notionToken });

    const response = await notion.search({
      filter: { property: "object", value: "page" },
      sort: { direction: "descending", timestamp: "last_edited_time" },
      page_size: 20,
    });

    const pages = response.results
      .filter((r): r is typeof r & { object: "page" } => r.object === "page")
      .map((page) => {
        let title = "제목 없음";
        if ("properties" in page) {
          const titleProp = page.properties["title"] || page.properties["Name"] || page.properties["이름"];
          if (titleProp && titleProp.type === "title" && titleProp.title.length > 0) {
            title = titleProp.title.map((t: { plain_text: string }) => t.plain_text).join("");
          }
        } else if ("title" in page && Array.isArray((page as { title?: Array<{ plain_text: string }> }).title)) {
          const titleArr = (page as { title?: Array<{ plain_text: string }> }).title;
          if (titleArr) title = titleArr.map(t => t.plain_text).join("");
        }

        return {
          id: page.id,
          title,
          url: "url" in page ? (page as { url: string }).url : "",
        };
      });

    res.json(pages);
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "노션 페이지 목록 조회 실패" });
  }
});

export default router;
