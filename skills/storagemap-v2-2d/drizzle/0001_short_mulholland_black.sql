CREATE TABLE `furniture` (
	`furnitureId` varchar(36) NOT NULL,
	`spaceId` varchar(36) NOT NULL,
	`name` varchar(30) NOT NULL,
	`type` enum('drawer','wardrobe','bookshelf','shelf','storage_box','cabinet','desk','locker','other'),
	`photoUrl` text,
	`posX` int NOT NULL DEFAULT 0,
	`posY` int NOT NULL DEFAULT 0,
	`width` int NOT NULL DEFAULT 100,
	`height` int NOT NULL DEFAULT 60,
	`color` varchar(7) NOT NULL DEFAULT '#9333ea',
	`zonesJson` json,
	`notes` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `furniture_furnitureId` PRIMARY KEY(`furnitureId`)
);
--> statement-breakpoint
CREATE TABLE `history` (
	`historyId` varchar(36) NOT NULL,
	`itemId` varchar(36) NOT NULL,
	`fromFurnitureId` varchar(36),
	`fromZoneId` varchar(36),
	`toFurnitureId` varchar(36) NOT NULL,
	`toZoneId` varchar(36),
	`movedAt` timestamp NOT NULL DEFAULT (now()),
	`note` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `history_historyId` PRIMARY KEY(`historyId`)
);
--> statement-breakpoint
CREATE TABLE `items` (
	`itemId` varchar(36) NOT NULL,
	`userId` int NOT NULL,
	`name` varchar(60) NOT NULL,
	`furnitureId` varchar(36) NOT NULL,
	`zoneId` varchar(36),
	`category` enum('electronics','clothing','living_goods','documents','tools','teaching_materials','stationery','other'),
	`tags` json,
	`memo` text,
	`photoUrl` text,
	`quantity` int NOT NULL DEFAULT 1,
	`context` enum('home','classroom','office','common') NOT NULL DEFAULT 'home',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `items_itemId` PRIMARY KEY(`itemId`)
);
--> statement-breakpoint
CREATE TABLE `spaces` (
	`spaceId` varchar(36) NOT NULL,
	`userId` int NOT NULL,
	`name` varchar(100) NOT NULL,
	`description` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `spaces_spaceId` PRIMARY KEY(`spaceId`)
);
--> statement-breakpoint
CREATE TABLE `zones` (
	`zoneId` varchar(36) NOT NULL,
	`furnitureId` varchar(36) NOT NULL,
	`name` varchar(20) NOT NULL,
	`positionDesc` varchar(50),
	`photoUrl` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `zones_zoneId` PRIMARY KEY(`zoneId`)
);
--> statement-breakpoint
CREATE INDEX `furniture_spaceId_idx` ON `furniture` (`spaceId`);--> statement-breakpoint
CREATE INDEX `history_itemId_idx` ON `history` (`itemId`);--> statement-breakpoint
CREATE INDEX `history_movedAt_idx` ON `history` (`movedAt`);--> statement-breakpoint
CREATE INDEX `items_userId_idx` ON `items` (`userId`);--> statement-breakpoint
CREATE INDEX `items_furnitureId_idx` ON `items` (`furnitureId`);--> statement-breakpoint
CREATE INDEX `items_zoneId_idx` ON `items` (`zoneId`);--> statement-breakpoint
CREATE INDEX `items_name_idx` ON `items` (`name`);--> statement-breakpoint
CREATE INDEX `spaces_userId_idx` ON `spaces` (`userId`);--> statement-breakpoint
CREATE INDEX `zones_furnitureId_idx` ON `zones` (`furnitureId`);