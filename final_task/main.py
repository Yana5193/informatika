import sys
import sqlite3
import pandas as pd
import os
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets, uic, QtCore
from fpdf import FPDF

# Пути к файлам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_path(filename): return os.path.join(BASE_DIR, filename)

def setup_database():
    conn = sqlite3.connect(get_path('mental_health.db'))
    cursor = conn.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS Departments (id_dept INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS Employees (id_emp INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, position TEXT, dept_id INTEGER, password TEXT);
    CREATE TABLE IF NOT EXISTS Test_List (id_test INTEGER PRIMARY KEY AUTOINCREMENT, test_name TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS Questions (id_quest INTEGER PRIMARY KEY AUTOINCREMENT, test_id INTEGER, quest_text TEXT);
    CREATE TABLE IF NOT EXISTS Test_logs (id_log INTEGER PRIMARY KEY AUTOINCREMENT, emp_id INTEGER, test_id INTEGER, date_passed DATETIME DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS Recommendations (id_rec INTEGER PRIMARY KEY AUTOINCREMENT, min_score INTEGER, max_score INTEGER, advice_text TEXT);
    CREATE TABLE IF NOT EXISTS Mental_Scores (id_score INTEGER PRIMARY KEY AUTOINCREMENT, log_id INTEGER, total_points INTEGER, status TEXT);
    ''')
    
    cursor.execute("DELETE FROM Recommendations")
    cursor.executemany("INSERT INTO Recommendations (min_score, max_score, advice_text) VALUES (?,?,?)", 
                       [(0, 15, 'Все в порядке.'), (16, 30, 'Рекомендуем отдых.'), (31, 100, 'Высокий уровень стресса!')])
    conn.commit()
    return conn

class MentalApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(get_path('interface.ui'), self)
        self.conn = setup_database()
        self.current_role = None 
        
        # Кнопки
        self.btn_worker_start.clicked.connect(self.login_worker)
        self.btn_expert_auth.clicked.connect(self.login_expert)
        if hasattr(self, 'btn_back_to_menu'): self.btn_back_to_menu.clicked.connect(self.back)
        
        self.btn_add_employee.clicked.connect(self.add_emp)
        self.btn_create_test.clicked.connect(self.add_test)
        self.btn_add_quest.clicked.connect(self.add_q)
        
        self.btn_show_dist.clicked.connect(self.plot_hist)
        self.btn_show_depts.clicked.connect(self.plot_pie)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_logout.clicked.connect(self.back)

        for i in range(1, 6):
            btn = getattr(self, f'btn_ans_{i}', None)
            if btn: btn.clicked.connect(lambda ch, v=i: self.answer(v))
            
        self.refresh()

    def refresh(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT full_name FROM Employees")
        self.combo_users.clear()
        self.combo_users.addItems([r[0] for r in cursor.fetchall()])
        cursor.execute("SELECT test_name FROM Test_List")
        self.combo_tests.clear()
        self.combo_tests.addItems([r[0] for r in cursor.fetchall()])

    def back(self):
        self.current_role = None
        self.refresh()
        self.btn_reftesh.setCurrentIndex(0)

    # --- ТАБЛИЦА С РАЗГРАНИЧЕНИЕМ ПРАВ ---
    def update_admin_table(self):
        if not hasattr(self, 'tableWidget'): return
        cursor = self.conn.cursor()
        
        cursor.execute('''SELECT e.full_name, d.title, e.position, t.test_name, ms.total_points, tl.date_passed 
                          FROM Employees e 
                          JOIN Departments d ON e.dept_id = d.id_dept
                          JOIN Test_logs tl ON e.id_emp = tl.emp_id 
                          JOIN Test_List t ON tl.test_id = t.id_test
                          JOIN Mental_Scores ms ON tl.id_log = ms.log_id''')
        data = cursor.fetchall()
        self.tableWidget.setRowCount(len(data))

        if self.current_role == "Менеджер":
            self.tableWidget.setColumnCount(3)
            self.tableWidget.setHorizontalHeaderLabels(["ФИО", "Тест", "Дата прохождения"])
        else:
            self.tableWidget.setColumnCount(7)
            self.tableWidget.setHorizontalHeaderLabels(["ФИО", "Отдел", "Должность", "Тест", "Баллы", "Дата", "Состояние"])

        for r_idx, row in enumerate(data):
            if self.current_role == "Психолог":
                score = row[4]
                if score >= 31: st, color = "НУЖНА БЕСЕДА", QtCore.Qt.red
                elif score >= 16: st, color = "В зоне риска", QtCore.Qt.yellow
                else: st, color = "Норма", QtCore.Qt.green

                for c_idx, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setBackground(color)
                    self.tableWidget.setItem(r_idx, c_idx, item)
                
                st_item = QtWidgets.QTableWidgetItem(st)
                st_item.setBackground(color)
                self.tableWidget.setItem(r_idx, 6, st_item)
            else:
                self.tableWidget.setItem(r_idx, 0, QtWidgets.QTableWidgetItem(str(row[0])))
                self.tableWidget.setItem(r_idx, 1, QtWidgets.QTableWidgetItem(str(row[3])))
                self.tableWidget.setItem(r_idx, 2, QtWidgets.QTableWidgetItem(str(row[5])))

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        
        try: self.tableWidget.itemDoubleClicked.disconnect()
        except: pass
        if self.current_role == "Психолог":
            self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.tableWidget.itemDoubleClicked.connect(self.on_row_clicked)

    def on_row_clicked(self, item):
        row = item.row()
        name = self.tableWidget.item(row, 0).text()
        status = self.tableWidget.item(row, 6).text()
        if status == "НУЖНА БЕСЕДА":
            QtWidgets.QMessageBox.critical(self, "Внимание", f"Сотрудник {name} требует личной беседы.")
        else:
            QtWidgets.QMessageBox.information(self, "Инфо", f"Сотрудник: {name}\nСостояние: {status}")

    # --- АДМИН-ФУНКЦИИ ---
    def add_emp(self):
        n, ok1 = QtWidgets.QInputDialog.getText(self, "Менеджер", "ФИО:")
        d, ok2 = QtWidgets.QInputDialog.getText(self, "Менеджер", "Отдел:")
        pos, ok3 = QtWidgets.QInputDialog.getText(self, "Менеджер", "Должность:")
        p, ok4 = QtWidgets.QInputDialog.getText(self, "Менеджер", "Пароль:")
        if all([ok1, ok2, ok3, ok4]):
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO Departments (title) VALUES (?)", (d,))
            cursor.execute("SELECT id_dept FROM Departments WHERE title=?", (d,))
            d_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO Employees (full_name, position, dept_id, password) VALUES (?,?,?,?)", (n, pos, d_id, p))
            self.conn.commit()
            self.refresh()

    def add_test(self):
        n, ok = QtWidgets.QInputDialog.getText(self, "Психолог", "Название теста:")
        if ok and n:
            self.conn.cursor().execute("INSERT OR IGNORE INTO Test_List (test_name) VALUES (?)", (n,))
            self.conn.commit()
            self.refresh()

    def add_q(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT test_name FROM Test_List")
        tests = [r[0] for r in cursor.fetchall()]
        if not tests: return
        t_name, ok1 = QtWidgets.QInputDialog.getItem(self, "Психолог", "Выберите тест:", tests, 0, False)
        if ok1 and t_name:
            txt, ok2 = QtWidgets.QInputDialog.getText(self, "Психолог", "Текст вопроса:")
            if ok2 and txt:
                cursor.execute("SELECT id_test FROM Test_List WHERE test_name=?", (t_name,))
                t_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO Questions (test_id, quest_text) VALUES (?,?)", (t_id, txt))
                self.conn.commit()

    # --- ТЕСТИРОВАНИЕ ---
    def login_worker(self):
        name = self.combo_users.currentText()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id_emp, password FROM Employees WHERE full_name=?", (name,))
        res = cursor.fetchone()
        if res:
            p, ok = QtWidgets.QInputDialog.getText(self, 'Вход', 'Пароль:', QtWidgets.QLineEdit.Password)
            if ok and p == str(res[1]):
                cursor.execute("SELECT id_test FROM Test_List WHERE test_name=?", (self.combo_tests.currentText(),))
                self.start_t(res[0], cursor.fetchone()[0])

    def start_t(self, e_id, t_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT quest_text FROM Questions WHERE test_id=?", (t_id,))
        self.qs = cursor.fetchall()
        if not self.qs: return
        self.e_id, self.t_id, self.idx, self.score = e_id, t_id, 0, 0
        cursor.execute("INSERT INTO Test_logs (emp_id, test_id) VALUES (?,?)", (e_id, t_id))
        self.log_id = cursor.lastrowid
        self.btn_reftesh.setCurrentIndex(1)
        self.show_q()

    def show_q(self):
        if self.idx < len(self.qs):
            self.lbl_question_text.setText(self.qs[self.idx][0])
            self.test_progress.setValue(int((self.idx / len(self.qs)) * 100))
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT advice_text FROM Recommendations WHERE ? BETWEEN min_score AND max_score", (self.score,))
            adv = cursor.fetchone()[0]
            cursor.execute("INSERT INTO Mental_Scores (log_id, total_points, status) VALUES (?, ?, 'Done')", (self.log_id, self.score))
            self.conn.commit()
            self.lbl_user_score.setText(f"Результат: {self.score} баллов")
            self.lbl_user_advice.setText(adv)
            self.btn_reftesh.setCurrentIndex(2)

    def answer(self, v):
        self.score += v
        self.idx += 1
        self.show_q()

    def login_expert(self):
        role, ok1 = QtWidgets.QInputDialog.getItem(self, "Вход", "Роль:", ["Менеджер", "Психолог"], 0, False)
        pwd, ok2 = QtWidgets.QInputDialog.getText(self, "Пароль", "Введите:", QtWidgets.QLineEdit.Password)
        creds = {"Менеджер": "manager77", "Психолог": "psycho88"}
        if ok2 and pwd == creds[role]:
            self.current_role = role
            self.btn_reftesh.setCurrentIndex(3)
            self.update_admin_table()
            self.btn_add_employee.setVisible(role == "Менеджер")
            self.btn_create_test.setVisible(role == "Психолог")
            self.btn_add_quest.setVisible(role == "Психолог")

    # --- ГРАФИКИ И PDF ---
    def plot_hist(self, save=False):
        cursor = self.conn.cursor()
        cursor.execute("SELECT total_points FROM Mental_Scores")
        d = [r[0] for r in cursor.fetchall()]
        if not d: return
        plt.figure(figsize=(6, 4))
        plt.hist(d, bins=5, color='skyblue', edgecolor='black')
        plt.title("Распределение баллов")
        plt.xlabel("Баллы"); plt.ylabel("Сотрудники")
        plt.tight_layout()
        if save: plt.savefig(get_path("h.png")); plt.close()
        else: plt.show()

    def plot_pie(self, save=False):
        cursor = self.conn.cursor()
        cursor.execute('''SELECT d.title, AVG(ms.total_points) as avg_score FROM Departments d 
                          JOIN Employees e ON d.id_dept = e.dept_id
                          JOIN Test_logs tl ON e.id_emp = tl.emp_id
                          JOIN Mental_Scores ms ON tl.id_log = ms.log_id GROUP BY d.title ORDER BY avg_score DESC''')
        res = cursor.fetchall()
        if not res: return
        depts, scores = [r[0] for r in res], [r[1] for r in res]
        colors = ['red' if s > 30 else 'orange' if s > 15 else 'green' for s in scores]
        plt.figure(figsize=(10, 6))
        plt.barh(depts, scores, color=colors, edgecolor='black')
        plt.axvline(x=31, color='red', linestyle='--', label='Риск')
        plt.title("Средний стресс по отделам"); plt.xlabel("Баллы")
        plt.gca().invert_yaxis(); plt.tight_layout()
        if save: plt.savefig(get_path("d.png")); plt.close()
        else: plt.show()

    def export_pdf(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT e.full_name, ms.total_points FROM Employees e 
                              JOIN Test_logs tl ON e.id_emp = tl.emp_id 
                              JOIN Mental_Scores ms ON tl.id_log = ms.log_id''')
            rows = cursor.fetchall()
            if not rows: return
            
            # Генерируем картинки
            self.plot_hist(save=True)
            self.plot_pie(save=True)

            pdf = FPDF()
            pdf.add_page()
            f = get_path("DejaVuSans.ttf")
            if os.path.exists(f): 
                pdf.add_font('DejaVu', '', f, uni=True); pdf.set_font('DejaVu', '', 12)
            else: pdf.set_font('Arial', '', 12)
            
            pdf.cell(200, 10, txt="АНАЛИТИЧЕСКИЙ ОТЧЕТ", ln=1, align='C')
            pdf.ln(5)
            for r in rows: pdf.cell(200, 8, txt=f"Сотрудник: {r[0]} | Баллы: {r[1]}", ln=1)
            
            pdf.ln(10); pdf.cell(200, 10, txt="Визуальный анализ:", ln=1)
            pdf.image(get_path("h.png"), x=10, y=None, w=90)
            if os.path.exists(get_path("d.png")):
                pdf.image(get_path("d.png"), x=105, y=pdf.get_y() - 65, w=90)

            pdf.output(get_path("final_analytics.pdf"))
            for tmp in ["h.png", "d.png"]:
                if os.path.exists(get_path(tmp)): os.remove(get_path(tmp))
            QtWidgets.QMessageBox.information(self, "OK", "PDF отчет готов!")
        except Exception as e: print(e)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MentalApp()
    win.show()
    sys.exit(app.exec_())