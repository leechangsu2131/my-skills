CREATE TABLE `analysis_data` (
	`id` int AUTO_INCREMENT NOT NULL,
	`session_id` int NOT NULL,
	`student_answer_id` int,
	`file_url` text NOT NULL,
	`file_type` varchar(50) NOT NULL,
	`analysis_content` text,
	`uploaded_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `analysis_data_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `answer_keys` (
	`id` int AUTO_INCREMENT NOT NULL,
	`session_id` int NOT NULL,
	`pdf_url` text NOT NULL,
	`ocr_text` text,
	`extracted_answers` text,
	`uploaded_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `answer_keys_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `grading_results` (
	`id` int AUTO_INCREMENT NOT NULL,
	`student_answer_id` int NOT NULL,
	`session_id` int NOT NULL,
	`total_questions` int NOT NULL,
	`correct_count` int NOT NULL,
	`score` varchar(50) NOT NULL,
	`question_results` text,
	`result_pdf_url` text,
	`analysis_data` text,
	`graded_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `grading_results_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `grading_sessions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`user_id` int NOT NULL,
	`session_name` varchar(255) NOT NULL,
	`description` text,
	`total_questions` int DEFAULT 0,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `grading_sessions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `student_answers` (
	`id` int AUTO_INCREMENT NOT NULL,
	`session_id` int NOT NULL,
	`student_name` varchar(255) NOT NULL,
	`pdf_url` text NOT NULL,
	`ocr_text` text,
	`extracted_answers` text,
	`uploaded_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `student_answers_id` PRIMARY KEY(`id`)
);
