import sqlite3
import pandas as pd

connection = sqlite3.connect("baza.db")
cursor = connection.cursor()

# Создание таблиц
cursor.execute("""
    CREATE TABLE IF NOT EXISTS stores(
        id_store TEXT PRIMARY KEY,
        district TEXT,
        address TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS products(
        art INTEGER PRIMARY KEY,
        department TEXT,
        product_name TEXT,
        unit TEXT,
        quantity_per_pack INTEGER,
        price_per_pack INTEGER
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS movement_of_goods(
        id_operation INTEGER PRIMARY KEY NOT NULL UNIQUE,
        date TEXT,
        id_store TEXT,
        art INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        operation_type TEXT,
        FOREIGN KEY (id_store) REFERENCES stores(id_store),
        FOREIGN KEY (art) REFERENCES products(art)
    )
""")

file = 'C:/Users/anaer/OneDrive/Desktop/учеба/ИГУ/1 курс 2 семестр/информатика/бд/b.xlsx' 

movement_df = pd.read_excel(file, sheet_name='Движение товаров')
movement_df.columns = ['id_operation', 'date', 'id_store', 'art', 
                       'quantity', 'operation_type']

stores_df = pd.read_excel(file, sheet_name='Магазин')
stores_df.columns = ['id_store', 'district', 'address']

products_df = pd.read_excel(file, sheet_name='Товар')
products_df.columns = ['art', 'department', 'product_name', 'unit', 
                       'quantity_per_pack', 'price_per_pack']

stores_df.to_sql('stores', connection, if_exists='replace', index=False)
products_df.to_sql('products', connection, if_exists='replace', index=False)
movement_df.to_sql('movement_of_goods', connection, if_exists='replace', index=False)


cursor.execute("""
    SELECT
        SUM(m.quantity * p.price_per_pack) as total_revenue
    FROM movement_of_goods m
    JOIN products p ON m.art = p.art
    JOIN stores s ON m.id_store = s.id_store
    WHERE
        m.operation_type = 'Продажа'
        AND p.product_name LIKE 'Сметана%'
        AND s.address LIKE '%Самолетная улица%'
        AND date(m.date) BETWEEN '2024-10-07' AND '2024-10-14'
""")

result = cursor.fetchone()
print(f"\nСумма продаж сметаны: {result[0]:,.0f} руб.")
print("="*70)