import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router, protectedProcedure } from "./_core/trpc";
import { z } from "zod";
import {
  createGradingSession,
  getUserGradingSessions,
  getGradingSessionById,
  createStudentAnswer,
  createAnswerKey,
  getSessionStudentAnswers,
  getSessionGradingResults,
  getAnswerKeyBySessionId,
} from "./db";
import { performGrading, integrateAnalysisData } from "./gradingEngine";
import { uploadPdfToS3, uploadJsonToS3, downloadFileFromUrl } from "./fileUpload";
import { TRPCError } from "@trpc/server";

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
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

  grading: router({
    // 세션 생성
    createSession: protectedProcedure
      .input(z.object({
        sessionName: z.string().min(1),
        description: z.string().optional(),
        totalQuestions: z.number().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const result = await createGradingSession(
          ctx.user.id,
          input.sessionName,
          input.description,
          input.totalQuestions
        );
        return result;
      }),

    // 사용자의 세션 목록 조회
    listSessions: protectedProcedure.query(async ({ ctx }) => {
      return await getUserGradingSessions(ctx.user.id);
    }),

    // 세션 상세 조회
    getSession: protectedProcedure
      .input(z.object({ sessionId: z.number() }))
      .query(async ({ input }) => {
        return await getGradingSessionById(input.sessionId);
      }),

    // 학생 답안 업로드
    uploadStudentAnswer: protectedProcedure
      .input(z.object({
        sessionId: z.number(),
        studentName: z.string(),
        pdfUrl: z.string(),
      }))
      .mutation(async ({ input }) => {
        const result = await createStudentAnswer(
          input.sessionId,
          input.studentName,
          input.pdfUrl
        );
        return result;
      }),

    // 정답 업로드
    uploadAnswerKey: protectedProcedure
      .input(z.object({
        sessionId: z.number(),
        pdfUrl: z.string(),
      }))
      .mutation(async ({ input }) => {
        const result = await createAnswerKey(
          input.sessionId,
          input.pdfUrl
        );
        return result;
      }),

    // 세션의 학생 답안 목록
    getSessionStudents: protectedProcedure
      .input(z.object({ sessionId: z.number() }))
      .query(async ({ input }) => {
        return await getSessionStudentAnswers(input.sessionId);
      }),

    // 정답지 조회
    getAnswerKey: protectedProcedure
      .input(z.object({ sessionId: z.number() }))
      .query(async ({ input }) => {
        return await getAnswerKeyBySessionId(input.sessionId);
      }),

    // 채점 결과 조회
    getGradingResults: protectedProcedure
      .input(z.object({ sessionId: z.number() }))
      .query(async ({ input }) => {
        return await getSessionGradingResults(input.sessionId);
      }),

    // 채점 수행 (PDF 다운로드 기반)
    performGrading: protectedProcedure
      .input(z.object({
        sessionId: z.number(),
        studentAnswerId: z.number(),
        studentPdfUrl: z.string(),
        answerKeyPdfUrl: z.string(),
      }))
      .mutation(async ({ input }) => {
        try {
          // PDF 파일 다운로드
          const studentPdfBuffer = await downloadFileFromUrl(input.studentPdfUrl);
          const answerKeyPdfBuffer = await downloadFileFromUrl(input.answerKeyPdfUrl);

          // 채점 수행
          const result = await performGrading(
            studentPdfBuffer,
            answerKeyPdfBuffer,
            input.sessionId,
            input.studentAnswerId
          );

          return result;
        } catch (error) {
          console.error("Grading error:", error);
          throw new TRPCError({
            code: "INTERNAL_SERVER_ERROR",
            message: "채점 처리 중 오류가 발생했습니다.",
          });
        }
      }),

    // 파일 업로드 처리
    uploadFile: protectedProcedure
      .input(z.object({
        sessionId: z.number(),
        fileType: z.enum(["student", "answerKey", "analysis"]),
        fileBuffer: z.instanceof(Buffer),
        fileName: z.string(),
        studentName: z.string().optional(),
      }))
      .mutation(async ({ input }) => {
        // TODO: 실제 파일 업로드 및 S3 저장 구현
        return {
          success: true,
          url: "https://example.com/file.pdf",
        };
      }),
  }),
});

export type AppRouter = typeof appRouter;


