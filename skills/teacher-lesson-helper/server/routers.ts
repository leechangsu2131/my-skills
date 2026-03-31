import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, protectedProcedure, router } from "./_core/trpc";
import { z } from "zod";
import { storagePut } from "./storage";
import { extractTextFromPDF, detectLessons, extractLessonContent } from "./pdf-utils";
import {
  createTextbook,
  getTextbooksByUserId,
  getTextbookById,
  deleteTextbook,
  createLessonExtraction,
  getLessonsByTextbookId,
  getLessonByNumber,
  addRecentAccess,
  getRecentAccessesByUserId,
} from "./db";
import { TRPCError } from "@trpc/server";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  textbook: router({
    list: protectedProcedure.query(async ({ ctx }) => {
      return getTextbooksByUserId(ctx.user.id);
    }),

    create: protectedProcedure
      .input(
        z.object({
          title: z.string().min(1),
          subject: z.string().min(1),
          grade: z.number().int().min(1).max(6),
          semester: z.number().int().min(1).max(2),
          publisher: z.string().optional(),
          fileBuffer: z.instanceof(Buffer),
          fileName: z.string(),
        })
      )
      .mutation(async ({ ctx, input }) => {
        try {
          // Upload PDF to S3
          const fileKey = `textbooks/${ctx.user.id}/${Date.now()}-${input.fileName}`;
          const { url: fileUrl } = await storagePut(fileKey, input.fileBuffer, "application/pdf");

          // Extract text from PDF
          const { text, totalPages } = await extractTextFromPDF(input.fileBuffer);

          // Create textbook record
          const textbook = await createTextbook({
            userId: ctx.user.id,
            title: input.title,
            subject: input.subject,
            grade: input.grade,
            semester: input.semester,
            publisher: input.publisher,
            fileKey,
            fileUrl,
            totalPages,
          });

          // Detect and store lessons
          const detectedLessons = detectLessons(text);
          for (const lesson of detectedLessons) {
            const content = extractLessonContent(text, lesson.lessonNumber, detectedLessons);
            await createLessonExtraction({
              textbookId: textbook.id,
              lessonNumber: lesson.lessonNumber,
              title: content.title,
              content: content.content,
            });
          }

          return textbook;
        } catch (error) {
          console.error("Error creating textbook:", error);
          throw new TRPCError({
            code: "INTERNAL_SERVER_ERROR",
            message: "Failed to create textbook",
          });
        }
      }),

    getById: protectedProcedure
      .input(z.object({ id: z.number() }))
      .query(async ({ ctx, input }) => {
        const textbook = await getTextbookById(input.id);
        if (!textbook || textbook.userId !== ctx.user.id) {
          throw new TRPCError({ code: "NOT_FOUND" });
        }
        return textbook;
      }),

    delete: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(async ({ ctx, input }) => {
        const textbook = await getTextbookById(input.id);
        if (!textbook || textbook.userId !== ctx.user.id) {
          throw new TRPCError({ code: "NOT_FOUND" });
        }
        await deleteTextbook(input.id);
        return { success: true };
      }),
  }),

  lesson: router({
    listByTextbook: protectedProcedure
      .input(z.object({ textbookId: z.number() }))
      .query(async ({ ctx, input }) => {
        const textbook = await getTextbookById(input.textbookId);
        if (!textbook || textbook.userId !== ctx.user.id) {
          throw new TRPCError({ code: "NOT_FOUND" });
        }
        return getLessonsByTextbookId(input.textbookId);
      }),

    getByNumber: protectedProcedure
      .input(z.object({ textbookId: z.number(), lessonNumber: z.number() }))
      .query(async ({ ctx, input }) => {
        const textbook = await getTextbookById(input.textbookId);
        if (!textbook || textbook.userId !== ctx.user.id) {
          throw new TRPCError({ code: "NOT_FOUND" });
        }

        const lesson = await getLessonByNumber(input.textbookId, input.lessonNumber);
        if (!lesson) {
          throw new TRPCError({ code: "NOT_FOUND" });
        }

        // Record access
        await addRecentAccess({
          userId: ctx.user.id,
          textbookId: input.textbookId,
          lessonNumber: input.lessonNumber,
        });

        return lesson;
      }),
  }),

  recentAccess: router({
    list: protectedProcedure.query(async ({ ctx }) => {
      return getRecentAccessesByUserId(ctx.user.id, 10);
    }),
  }),
});

export type AppRouter = typeof appRouter;
