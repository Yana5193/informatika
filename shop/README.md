# БД "Продажи в магазине"
Запросы:
### 1)в окне «Новая продажа»
SELECT id_product, name_product, price, quanite_at_strogare 
FROM products
### 2)Создание нового чека
INSERT INTO receipts (created_at, id_cashier) 
VALUES (?, ?)
### 3)Добавление купленного товара в чек
INSERT INTO sale_items (id_check, id_product, quantity) 
VALUES (?, ?, ?)
### 4)Списание товара со склада
UPDATE products 
SET quanite_at_strogare = quanite_at_strogare - ? 
WHERE id_product = ?
### 5)Основной запрос отчёта (продажи по товарам)

SELECT p.name_product,

       SUM(s.quantity) as total_qty, 
       
       SUM(p.price * s.quantity) as total_sum
       
FROM sale_items s

JOIN products p ON p.id_product = s.id_product

JOIN receipts r ON r.id_check = s.id_check

WHERE DATE(r.created_at) = ?

GROUP BY p.name_product

ORDER BY total_sum DESC
### 6)Запрос для общей выручки за день
SELECT SUM(p.price * s.quantity)

FROM sale_items s

JOIN products p ON p.id_product = s.id_product

JOIN receipts r ON r.id_check = s.id_check

WHERE DATE(r.created_at) = ?
