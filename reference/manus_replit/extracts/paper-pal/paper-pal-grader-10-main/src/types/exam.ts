export interface StudentAnswer {
  questionNumber: number;
  answer: string;
  type: 'objective' | 'subjective';
}

export interface AnswerKey {
  questionNumber: number;
  answer: string;
  type: 'objective' | 'subjective';
  points: number;
}

export interface GradingResult {
  questionNumber: number;
  studentAnswer: string;
  correctAnswer: string;
  isCorrect: boolean;
  points: number;
  earnedPoints: number;
  type: 'objective' | 'subjective';
}

export interface ExamResult {
  studentName: string;
  fileName: string;
  answers: StudentAnswer[];
  results: GradingResult[];
  totalScore: number;
  maxScore: number;
  correctCount: number;
  totalQuestions: number;
  pdfFile: File;
  analysisContent?: string;
}

export type AppStep = 'upload-answer-key' | 'upload-exams' | 'review-answers' | 'grading' | 'results';
