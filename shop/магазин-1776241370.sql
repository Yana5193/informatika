CREATE TABLE IF NOT EXISTS `categories` (
	`id_category` integer primary key NOT NULL UNIQUE,
	`name_of_category` TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS `products` (
	`id_product` integer primary key NOT NULL UNIQUE,
	`name_product` TEXT NOT NULL,
	`price` REAL NOT NULL,
	`id_category` INTEGER NOT NULL,
	`quanite_at_strogare` REAL NOT NULL,
FOREIGN KEY(`id_category`) REFERENCES `categories`(`id_category`)
);
CREATE TABLE IF NOT EXISTS `sale_items` (
	`id_sale` integer primary key NOT NULL UNIQUE,
	`id_check` INTEGER NOT NULL,
	`id_product` INTEGER NOT NULL,
	`quantity` REAL NOT NULL,
FOREIGN KEY(`id_check`) REFERENCES `receipts`(`id_check`),
FOREIGN KEY(`id_product`) REFERENCES `products`(`id_product`)
);
CREATE TABLE IF NOT EXISTS `receipts` (
	`id_check` integer primary key NOT NULL UNIQUE,
	`created_at` REAL NOT NULL,
	`null` INTEGER NOT NULL,
FOREIGN KEY(`null`) REFERENCES `employees`(`id`)
);
CREATE TABLE IF NOT EXISTS `employees` (
	`id` integer primary key NOT NULL UNIQUE,
	`name` TEXT NOT NULL,
	`surname` TEXT NOT NULL,
	`id_job_tittle` INTEGER NOT NULL,
FOREIGN KEY(`id_job_tittle`) REFERENCES `jobs_titles`(`id`)
);

CREATE TABLE IF NOT EXISTS `jobs_titles` (
	`id` integer primary key NOT NULL UNIQUE,
	`name` TEXT NOT NULL
);
