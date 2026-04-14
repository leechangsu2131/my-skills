CREATE TABLE `lesson_extractions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`textbookId` int NOT NULL,
	`lessonNumber` int NOT NULL,
	`title` varchar(255),
	`startPage` int,
	`endPage` int,
	`content` longtext,
	`extractedAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `lesson_extractions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `recent_accesses` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`textbookId` int NOT NULL,
	`lessonNumber` int,
	`accessedAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `recent_accesses_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `textbooks` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`title` varchar(255) NOT NULL,
	`subject` varchar(100) NOT NULL,
	`grade` int NOT NULL,
	`semester` int NOT NULL,
	`publisher` varchar(255),
	`fileKey` varchar(500) NOT NULL,
	`fileUrl` text NOT NULL,
	`totalPages` int,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `textbooks_id` PRIMARY KEY(`id`)
);
