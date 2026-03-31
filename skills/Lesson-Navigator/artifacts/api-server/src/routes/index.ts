import { Router, type IRouter } from "express";
import healthRouter from "./health";
import textbooksRouter from "./textbooks/index";
import lessonsRouter from "./lessons";
import notionRouter from "./notion";

const router: IRouter = Router();

router.use(healthRouter);
router.use("/textbooks", textbooksRouter);
router.use("/lessons", lessonsRouter);
router.use("/notion", notionRouter);

export default router;
