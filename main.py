import sys
import sqlite3
import csv
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QLineEdit, QLabel, QHBoxLayout, 
                             QHeaderView, QComboBox, QDialog)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor

# Поток для работы с БД
class DatabaseWorker(QThread):
    booksLoaded = pyqtSignal(list)

    def __init__(self, search_query=""):
        super().__init__()
        self.search_query = search_query
    
    def run(self):
        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()
        query = "SELECT title, author, status FROM books"
        params = ()
        if self.search_query:
            query += " WHERE title LIKE ? OR author LIKE ?"
            params = (f'%{self.search_query}%', f'%{self.search_query}%')
        cursor.execute(query, params)
        books = cursor.fetchall()
        conn.close()
        self.booksLoaded.emit(books)

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход в библиотеку")
        self.setGeometry(200, 200, 300, 150)
        layout = QVBoxLayout()
        
        self.roleComboBox = QComboBox(self)
        self.roleComboBox.addItems(["Гость", "Админ"])
        layout.addWidget(QLabel("Выберите роль:"))
        layout.addWidget(self.roleComboBox)
        
        self.loginButton = QPushButton("Войти", self)
        self.loginButton.clicked.connect(self.accept)
        layout.addWidget(self.loginButton)
        
        self.setLayout(layout)
    
    def get_role(self):
        return "admin" if self.roleComboBox.currentText() == "Админ" else "guest"

class LibraryApp(QWidget):
    def __init__(self, user_role, username):
        super().__init__()
        self.user_role = user_role  # "admin" или "guest"
        self.username = username  # Сохраняем имя пользователя
        self.user_role = user_role  # Возможные роли: "admin", "guest"
        self.initUI()
        self.initDB()
        self.loadBooks()
        self.updateUI()

    def initUI(self):
        self.setWindowTitle('Библиотека')
        self.setGeometry(100, 100, 700, 500)
        
        layout = QVBoxLayout()
        
        self.searchInput = QLineEdit(self)
        self.searchInput.setPlaceholderText("Поиск по названию или автору")
        self.searchInput.textChanged.connect(self.searchBooks)
        layout.addWidget(self.searchInput)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Название', 'Автор', 'Статус'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        
        addLayout = QHBoxLayout()
        self.bookInput = QLineEdit(self)
        self.authorInput = QLineEdit(self)
        self.bookInput.setPlaceholderText("Название книги")
        self.authorInput.setPlaceholderText("Автор")
        addLayout.addWidget(self.bookInput)
        addLayout.addWidget(self.authorInput)
        layout.addLayout(addLayout)
        
        self.statusComboBox = QComboBox(self)
        self.statusComboBox.addItems(["Доступна", "Занята"])
        layout.addWidget(self.statusComboBox)
        
        self.addButton = QPushButton('Добавить книгу', self)
        self.addButton.clicked.connect(self.addBook)
        self.addButton.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        layout.addWidget(self.addButton)
        
        self.borrowButton = QPushButton('Взять/Вернуть книгу', self)
        self.borrowButton.clicked.connect(self.toggleStatus)
        # self.borrowButton.setStyleSheet("background-color: yellow; color: white; font-weight: bold;")
        layout.addWidget(self.borrowButton)
        
        self.historyButton = QPushButton("История книг", self)
        self.historyButton.clicked.connect(self.open_history)
        layout.addWidget(self.historyButton)
        
        self.deleteButton = QPushButton('Удалить книгу', self)
        self.deleteButton.clicked.connect(self.deleteBook)
        self.deleteButton.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        layout.addWidget(self.deleteButton)
        
        self.refreshButton = QPushButton('Обновить список', self)
        self.refreshButton.clicked.connect(self.loadBooks)
        # self.refreshButton.setStyleSheet("background-color: blue; color: white; font-weight: bold;")
        layout.addWidget(self.refreshButton)
        
        self.logoutButton = QPushButton('Выйти из аккаунта', self)
        self.logoutButton.clicked.connect(self.logout)
        self.logoutButton.setStyleSheet("background-color: brown; color: white; font-weight: bold;")
        layout.addWidget(self.logoutButton)
        

        
        self.setLayout(layout)

    def initDB(self):
        try:
            conn = sqlite3.connect("library.db")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                book_title TEXT NOT NULL,
                date_taken TEXT NOT NULL,
                date_returned TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT CHECK(status IN ('Доступна', 'Занята')) DEFAULT 'Доступна'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'guest')) DEFAULT 'guest'
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        finally:
            conn.close()
    
    def loadBooks(self, search_query=""):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()  # Останавливаем предыдущий поток, если он запущен

        self.worker = DatabaseWorker(search_query)
        self.worker.booksLoaded.connect(self.displayBooks)
        self.worker.start()
    
    def displayBooks(self, books):
        self.table.setRowCount(0)
        for row_idx, row_data in enumerate(books):
            self.table.insertRow(row_idx)
            for col_idx, col_data in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))
    
    def addBook(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, 'Ошибка', 'У вас нет прав на добавление книг')
            return
        title, author, status = self.bookInput.text(), self.authorInput.text(), self.statusComboBox.currentText()
        if title and author:
            conn = sqlite3.connect("library.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO books (title, author, status) VALUES (?, ?, ?)", (title, author, status))
            conn.commit()
            conn.close()
            self.loadBooks()
            self.bookInput.clear()
            self.authorInput.clear()
        else:
            QMessageBox.warning(self, 'Ошибка', 'Введите название и автора книги')
        
    def deleteBook(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, 'Ошибка', 'У вас нет прав на удаление книг')
            return
        
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, 'Ошибка', 'Выберите книгу для удаления')
            return
        
        title = self.table.item(selected_row, 0).text()
        reply = QMessageBox.question(self, 'Подтверждение', f'Удалить книгу "{title}"?', QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect("library.db")  # Создаём соединение
            cursor = conn.cursor()
            cursor.execute("DELETE FROM books WHERE title = ?", (title,))
            conn.commit()
            conn.close()
            self.loadBooks()

    def toggleStatus(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, 'Ошибка', 'Выберите книгу')
            return

        title = self.table.item(selected_row, 0).text()
        current_status = self.table.item(selected_row, 2).text()
        new_status = 'Доступна' if current_status == 'Занята' else 'Занята'

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        if new_status == "Занята":
            cursor.execute("INSERT INTO history (username, book_title, date_taken) VALUES (?, ?, datetime('now'))", 
                        (self.username, title))
        else:
            cursor.execute("UPDATE history SET date_returned = datetime('now') WHERE book_title = ? AND username = ? AND date_returned IS NULL", 
                        (title, self.username))

        cursor.execute("UPDATE books SET status = ? WHERE title = ?", (new_status, title))
        conn.commit()
        conn.close()

        self.loadBooks()
        
    def borrow_book(self, username, book_title):
        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        # Добавляем запись о взятии книги
        cursor.execute("INSERT INTO history (username, book_title, date_taken, date_returned) VALUES (?, ?, datetime('now'), NULL)", 
                    (username, book_title))

        # Обновляем статус книги
        cursor.execute("UPDATE books SET status = 'Занята' WHERE title = ?", (book_title,))
        
        conn.commit()
        conn.close()

    def return_book(self, username, book_title):
        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        # Обновляем запись, указывая дату возврата
        cursor.execute("""
            UPDATE history 
            SET date_returned = datetime('now') 
            WHERE username = ? AND book_title = ? AND date_returned IS NULL
        """, (username, book_title))

        # Обновляем статус книги
        cursor.execute("UPDATE books SET status = 'Доступна' WHERE title = ?", (book_title,))
        
        conn.commit()
        conn.close()

    def open_history(self):
        self.history_window = HistoryWindow()
        self.history_window.exec_()

    def closeEvent(self, event):
        conn = sqlite3.connect("library.db")
        conn.close()
        event.accept()

    def logout(self):
        self.close()  # Закрываем текущее окно
        auth_dialog = AuthDialog()
        
        if auth_dialog.exec_() == QDialog.Accepted:
            user_role = auth_dialog.user_role  # Получаем новую роль после входа
            self.__init__(user_role, self.username)  # Перезапускаем окно с новой ролью
            self.show()
            
    def searchBooks(self):
        search_query = self.searchInput.text()
        self.loadBooks(search_query)
    
    def updateUI(self):
        is_admin = self.user_role == "admin"
        
        # Скрываем или показываем элементы в зависимости от роли пользователя
        self.bookInput.setVisible(is_admin)
        self.authorInput.setVisible(is_admin)
        self.statusComboBox.setVisible(is_admin)
        self.addButton.setVisible(is_admin)
        self.deleteButton.setVisible(is_admin)
        self.historyButton.setVisible(is_admin)
        
        self.setStyleSheet("""
        QWidget {
            background-color: #f0f0f5;
        }
        
        QLineEdit, QComboBox {
            padding: 6px;
            border-radius: 5px;
            border: 1px solid #ccc;
        }
    """)

        # QPushButton:hover {
        #     background-color: #005a9e;
        # }

class AuthDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.username = ""  # Объявляем атрибут
        self.setWindowTitle("Авторизация")
        self.setGeometry(200, 200, 300, 200)
        
        layout = QVBoxLayout()
        
        self.usernameInput = QLineEdit(self)
        self.usernameInput.setPlaceholderText("Имя пользователя")
        layout.addWidget(QLabel("Имя пользователя:"))
        layout.addWidget(self.usernameInput)
        
        self.passwordInput = QLineEdit(self)
        self.passwordInput.setPlaceholderText("Пароль")
        self.passwordInput.setEchoMode(QLineEdit.Password)  # Скрывает пароль
        layout.addWidget(QLabel("Пароль:"))
        layout.addWidget(self.passwordInput)
        
        self.loginButton = QPushButton("Войти", self)
        self.loginButton.clicked.connect(self.authenticate)
        layout.addWidget(self.loginButton)
        
        self.registerButton = QPushButton("Зарегистрироваться", self)
        self.registerButton.clicked.connect(self.register)
        layout.addWidget(self.registerButton)
        
        self.setLayout(layout)
        
    def authenticate(self):
        username = self.usernameInput.text()
        password = self.passwordInput.text()

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()
        conn.close()

        if result:
            self.user_role = result[0]
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверные данные!")

    def register(self):
        username = self.usernameInput.text()
        password = self.passwordInput.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'guest')", (username, password))
            conn.commit()
            QMessageBox.information(self, "Успешно", "Аккаунт создан!")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", "Имя пользователя уже занято!")

        conn.close()

class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("История взятых книг")
        self.setGeometry(400, 200, 500, 400)

        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Пользователь", "Книга", "Дата"])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_history()

    def load_history(self):
        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("SELECT username, book_title, date_taken FROM history ORDER BY date_taken DESC")
        records = cursor.fetchall()

        self.table.setRowCount(len(records))

        for row, record in enumerate(records):
            for col, value in enumerate(record):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        conn.close()
    
class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("История взятых книг")
        self.setGeometry(400, 200, 800, 500)

        self.page = 0
        self.page_size = 20

        layout = QVBoxLayout()
        
        # Поиск и фильтрация
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по пользователю или книге")
        self.search_input.textChanged.connect(self.load_history)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Не возвращена", "Возвращена"])
        self.filter_combo.currentIndexChanged.connect(self.load_history)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.filter_combo)
        layout.addLayout(search_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Пользователь", "Книга", "Дата взятия", "Дата возврата"])
        layout.addWidget(self.table)

        # Кнопки
        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Удалить запись")
        self.delete_button.clicked.connect(self.delete_record)
        button_layout.addWidget(self.delete_button)

        self.export_button = QPushButton("Экспорт в CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        button_layout.addWidget(self.export_button)

        self.prev_button = QPushButton("Предыдущая страница")
        self.prev_button.clicked.connect(self.prev_page)
        button_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Следующая страница")
        self.next_button.clicked.connect(self.next_page)
        button_layout.addWidget(self.next_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.load_history()

    def load_history(self):
        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        search_query = self.search_input.text()
        filter_status = self.filter_combo.currentText()

        query = "SELECT username, book_title, date_taken, COALESCE(date_returned, 'Не возвращена') FROM history"
        conditions = []
        params = []

        if search_query:
            conditions.append("(username LIKE ? OR book_title LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        
        if filter_status == "Не возвращена":
            conditions.append("date_returned IS NULL")
        elif filter_status == "Возвращена":
            conditions.append("date_returned IS NOT NULL")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date_taken DESC LIMIT ? OFFSET ?"
        params.extend([self.page_size, self.page * self.page_size])

        cursor.execute(query, params)
        records = cursor.fetchall()

        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            for col, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                if record[3] == "Не возвращена":
                    item.setBackground(QColor(255, 200, 200))  # Красный фон для невозвращенных книг
                self.table.setItem(row, col, item)

        conn.close()

    def delete_record(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, 'Ошибка', 'Выберите запись для удаления.')
            return

        username = self.table.item(selected_row, 0).text()
        book_title = self.table.item(selected_row, 1).text()
        reply = QMessageBox.question(self, 'Подтверждение', f'Удалить запись о книге "{book_title}" пользователя {username}?', QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect("library.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history WHERE username = ? AND book_title = ?", (username, book_title))
            conn.commit()
            conn.close()
            self.load_history()

    def export_to_csv(self):
        with open('book_history.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Пользователь", "Книга", "Дата взятия", "Дата возврата"])
            for row in range(self.table.rowCount()):
                writer.writerow([self.table.item(row, col).text() for col in range(4)])
        QMessageBox.information(self, "Успех", "История успешно экспортирована в CSV!")

    def next_page(self):
        self.page += 1
        self.load_history()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.load_history()
        

def main():
    app = QApplication(sys.argv)
    auth_dialog = AuthDialog()

    if auth_dialog.exec_() == QDialog.Accepted:
        user_role = auth_dialog.user_role  # Получаем роль после входа
        username = auth_dialog.username  # Получаем имя пользователя
        window = LibraryApp(user_role, username)
        window.show()
        sys.exit(app.exec_())

if __name__ == '__main__':
    main()
