import { Router, type IRouter } from "express";
import healthRouter from "./health";
import spacesRouter from "./spaces";
import furnitureRouter from "./furniture";
import itemsRouter from "./items";

const router: IRouter = Router();

router.use(healthRouter);
router.use(spacesRouter);
router.use(furnitureRouter);
router.use(itemsRouter);

export default router;
