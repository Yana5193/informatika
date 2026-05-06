import sys
import sqlite3
import pandas as pd
import os
from PyQt5 import QtWidgets, uic

# Настройка путей, чтобы программа видела файлы в своей папке
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_path(filename):
    return os.path.join(BASE_DIR, filename)

# === 1. ПОДГОТОВКА БАЗЫ ДАННЫХ И EXCEL ===
def setup_database():
    conn = sqlite3.connect(get_path('mental_health.db'))
    cursor = conn.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS Departments (id_dept INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS Employees (id_emp INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, position TEXT, dept_id INTEGER);
    CREATE TABLE IF NOT EXISTS Questions (id_quest INTEGER PRIMARY KEY AUTOINCREMENT, quest_text TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS Test_logs (id_log INTEGER PRIMARY KEY AUTOINCREMENT, emp_id INTEGER, date_passed DATETIME DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS Recommendations (id_rec INTEGER PRIMARY KEY AUTOINCREMENT, min_score INTEGER, max_score INTEGER, advice_text TEXT);
    CREATE TABLE IF NOT EXISTS Mental_Scores (id_score INTEGER PRIMARY KEY AUTOINCREMENT, log_id INTEGER, total_points INTEGER, status TEXT, rec_id INTEGER);
    ''')
    
    recs = [
        (0, 15, 'Ваше состояние в норме. Вы отлично справляетесь с нагрузкой!'), 
        (16, 30, 'Выгорание близко. Рекомендуем обратить внимание на режим сна и отдыха.'), 
        (31, 50, 'Высокий уровень стресса. Пожалуйста, обратитесь к специалисту для консультации.')
    ]
    cursor.executemany("INSERT OR IGNORE INTO Recommendations (min_score, max_score, advice_text) VALUES (?,?,?)", recs)
    conn.commit()
    return conn

def import_all_from_excel(conn):
    try:
        cursor = conn.cursor()
        # Чистим старые данные перед обновлением
        cursor.execute("DELETE FROM Employees")
        cursor.execute("DELETE FROM Questions")
        
        # Читаем Excel (убедись, что файл рядом с кодом)
        df_emp = pd.read_excel(get_path('employees.xlsx'), sheet_name='Employees')
        for dept in df_emp['department'].unique():
            cursor.execute("INSERT OR IGNORE INTO Departments (title) VALUES (?)", (str(dept),))
        
        for _, row in df_emp.iterrows():
            cursor.execute("SELECT id_dept FROM Departments WHERE title=?", (str(row['department']),))
            d_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO Employees (full_name, position, dept_id) VALUES (?,?,?)", 
                           (str(row['full_name']), str(row['position']), d_id))

        df_quest = pd.read_excel(get_path('employees.xlsx'), sheet_name='Questions')
        for q_text in df_quest.iloc[:, 0]:
            cursor.execute("INSERT OR IGNORE INTO Questions (quest_text) VALUES (?)", (str(q_text),))
        
        conn.commit()
        print("Данные из Excel успешно загружены!")
    except Exception as e:
        print(f"Ошибка при чтении Excel: {e}")

# === 2. ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ===
class MentalHealthApp(QtWidgets.QMainWindow):
    def __init__(self, db_conn):
        super().__init__()
        uic.loadUi(get_path('interface.ui'), self)
        self.conn = db_conn
        self.questions = []
        self.current_q_idx = 0
        self.total_score = 0
        self.log_id = None

        # Устанавливаем начальную страницу (Выбор юзера)
        if hasattr(self, 'btn_reftesh'):
            self.btn_reftesh.setCurrentIndex(0)

        # Подключаем кнопку старта
        self.btn_start_test.clicked.connect(self.start_test)
        
        # Подключаем кнопку возврата (та, что "Завершить и выйти")
        if hasattr(self, 'btn_back_to_menu'):
            self.btn_back_to_menu.clicked.connect(self.return_to_main)
            
        # Подключаем кнопки ответов (1, 2, 3, 4, 5)
        self.buttons = []
        for i in range(1, 6):
            btn = self.findChild(QtWidgets.QPushButton, f'btn_ans_{i}')
            if btn:
                # Используем лямбду, чтобы передать номер кнопки как балл
                btn.clicked.connect(lambda checked, val=i: self.handle_answer(val))
                self.buttons.append(btn)
        
        self.load_user_list()

    def load_user_list(self):
        """Загрузка имен сотрудников в выпадающий список"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT full_name FROM Employees")
        users = [r[0] for r in cursor.fetchall()]
        self.combo_users.clear()
        self.combo_users.addItems(users)

    def start_test(self):
        """Начало тестирования"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id_quest, quest_text FROM Questions")
        self.questions = cursor.fetchall()

        if not self.questions:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Список вопросов пуст!")
            return

        name = self.combo_users.currentText()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Выберите сотрудника!")
            return

        cursor.execute("SELECT id_emp FROM Employees WHERE full_name=?", (name,))
        self.emp_id = cursor.fetchone()[0]
        
        # Создаем запись о начале теста
        cursor.execute("INSERT INTO Test_logs (emp_id) VALUES (?)", (self.emp_id,))
        self.log_id = cursor.lastrowid
        self.conn.commit()
        
        self.current_q_idx = 0
        self.total_score = 0
        
        # Переход на страницу ТЕСТА (индекс 1)
        self.btn_reftesh.setCurrentIndex(1)
        self.display_question()

    def display_question(self):
        """Отображение текущего вопроса"""
        if self.current_q_idx < len(self.questions):
            q_text = self.questions[self.current_q_idx][1]
            self.lbl_question_text.setText(q_text)
            
            # Обновление прогресса
            prog = int((self.current_q_idx / len(self.questions)) * 100)
            self.test_progress.setValue(prog)
        else:
            self.save_results()

    def handle_answer(self, val):
        """Обработка нажатия на кнопку ответа"""
        self.total_score += val
        self.current_q_idx += 1
        self.display_question()

    def save_results(self):
        """Переход к результатам сотрудника"""
        cursor = self.conn.cursor()
        # Получаем совет
        cursor.execute("SELECT advice_text FROM Recommendations WHERE ? BETWEEN min_score AND max_score", (self.total_score,))
        res = cursor.fetchone()
        advice = res[0] if res else "Тест пройден."
        
        # Сохраняем в базу
        cursor.execute("INSERT INTO Mental_Scores (log_id, total_points, status, rec_id) VALUES (?, ?, 'Завершено', 1)", 
                       (self.log_id, self.total_score))
        self.conn.commit()
        
        # Вывод на страницу результата (индекс 2)
        self.lbl_user_score.setText(f"Ваш результат: {self.total_score} баллов")
        self.lbl_user_advice.setText(advice)
        
        # Настройка текста, чтобы не обрезался
        self.lbl_user_score.setWordWrap(True)
        self.lbl_user_advice.setWordWrap(True)
        
        # Переключаем экран
        self.btn_reftesh.setCurrentIndex(2)

    def return_to_main(self):
        """Возврат на первую страницу"""
        self.btn_reftesh.setCurrentIndex(0)
        self.test_progress.setValue(0)
        self.load_user_list()

# === 3. ЗАПУСК ===
if __name__ == "__main__":
    database = setup_database()
    import_all_from_excel(database)
    
    app = QtWidgets.QApplication(sys.argv)
    window = MentalHealthApp(database)
    window.show()
    sys.exit(app.exec_())