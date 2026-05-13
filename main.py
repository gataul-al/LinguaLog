# FEATURE: Управление словарём - добавление, редактирование, удаление
# FEATURE: Режим тренажёра - проверка знаний, статистика, spaced repetition
# FEATURE: Экспорт/импорт данных - CSV, ZIP, резервное копирование
"""
LinguaLog - Персональный лингвистический тренажёр
Консольное приложение для изучения иностранных слов
Строго процедурный и функциональный стиль (без ООП)
"""

import sqlite3
import logging
import os
import json
import csv
import zipfile
import shutil
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ------------------------- Конфигурация -------------------------
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "lingua.db")

# Настройка логирования
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# ------------------------- Инициализация базы данных -------------------------
def init_db():
    """Создание таблиц words и review_stats если не существуют"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_word TEXT NOT NULL,
            translation TEXT NOT NULL,
            example TEXT,
            transcription TEXT,
            tags TEXT,
            added_date TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS review_stats (
            word_id INTEGER PRIMARY KEY,
            error_count INTEGER DEFAULT 0,
            last_reviewed TEXT,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("База данных инициализирована")

# ------------------------- Вспомогательные функции -------------------------
def get_date():
    return datetime.now().strftime("%Y-%m-%d")

def validate_not_empty(value, field_name):
    if not value or not value.strip():
        print(f"Ошибка: {field_name} не может быть пустым")
        return None
    return value.strip()

# ------------------------- 2.1. Модуль управления словарём -------------------------
def add_word():
    """Добавление новой карточки слова"""
    print("\n--- ДОБАВЛЕНИЕ НОВОГО СЛОВА ---")
    
    source_word = input("Исходное слово: ").strip()
    if not source_word:
        print("Ошибка: слово не может быть пустым")
        return
    
    translation = input("Перевод: ").strip()
    if not translation:
        print("Ошибка: перевод не может быть пустым")
        return
    
    example = input("Пример употребления (можно пропустить): ").strip()
    transcription = input("Транскрипция (можно пропустить): ").strip()
    tags = input("Теги через запятую (например: еда,путешествия): ").strip()
    added_date = get_date()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO words (source_word, translation, example, transcription, tags, added_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (source_word, translation, example, transcription, tags, added_date))
    word_id = cursor.lastrowid
    
    # Создаём запись в review_stats
    cursor.execute('''
        INSERT INTO review_stats (word_id, error_count, last_reviewed)
        VALUES (?, 0, ?)
    ''', (word_id, added_date))
    
    conn.commit()
    conn.close()
    
    logging.info(f"Добавлено слово: {source_word} -> {translation}")
    print(f"✅ Слово '{source_word}' добавлено!")

def list_words():
    """Просмотр всех слов с фильтрацией"""
    print("\n--- ФИЛЬТРАЦИЯ СЛОВ ---")
    filter_tag = input("Фильтр по тегу (Enter - пропустить): ").strip()
    filter_has_example = input("Только слова с примером? (да/нет): ").strip().lower()
    
    query = "SELECT id, source_word, translation, example, tags, added_date FROM words"
    conditions = []
    params = []
    
    if filter_tag:
        conditions.append("tags LIKE ?")
        params.append(f"%{filter_tag}%")
    
    if filter_has_example == "да":
        conditions.append("example IS NOT NULL AND example != ''")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY added_date DESC"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    words = cursor.fetchall()
    conn.close()
    
    if not words:
        print("\n📭 Нет слов, удовлетворяющих фильтрам")
        return
    
    print("\n" + "="*70)
    print("СПИСОК СЛОВ")
    print("="*70)
    for w in words:
        print(f"\n📖 ID: {w[0]}")
        print(f"   {w[1]} -> {w[2]}")
        if w[3]:
            print(f"   Пример: {w[3][:80]}...")
        print(f"   Теги: {w[4]} | Дата: {w[5]}")
        print("-"*40)

def view_word():
    """Просмотр полной информации о слове"""
    word_id = input("\nВведите ID слова: ").strip()
    if not word_id.isdigit():
        print("Ошибка: ID должен быть числом")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
    word = cursor.fetchone()
    conn.close()
    
    if not word:
        print("Слово не найдено")
        return
    
    print("\n" + "="*50)
    print(f"СЛОВО ID: {word[0]}")
    print(f"Исходное слово: {word[1]}")
    print(f"Перевод: {word[2]}")
    print(f"Пример: {word[3] if word[3] else '(не указан)'}")
    print(f"Транскрипция: {word[4] if word[4] else '(не указана)'}")
    print(f"Теги: {word[5] if word[5] else '(нет)'}")
    print(f"Дата добавления: {word[6]}")
    print("="*50)

def edit_word():
    """Редактирование карточки слова"""
    word_id = input("\nВведите ID слова для редактирования: ").strip()
    if not word_id.isdigit():
        print("Ошибка: ID должен быть числом")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
    word = cursor.fetchone()
    
    if not word:
        print("Слово не найдено")
        conn.close()
        return
    
    print(f"\nРедактирование слова: {word[1]} -> {word[2]}")
    print("(оставьте поле пустым, чтобы не менять)")
    
    new_source = input(f"Исходное слово [{word[1]}]: ").strip()
    new_translation = input(f"Перевод [{word[2]}]: ").strip()
    new_example = input(f"Пример [{word[3][:50] if word[3] else 'нет'}]: ").strip()
    new_transcription = input(f"Транскрипция [{word[4] if word[4] else 'нет'}]: ").strip()
    new_tags = input(f"Теги [{word[5] if word[5] else 'нет'}]: ").strip()
    
    updates = []
    params = []
    
    if new_source:
        updates.append("source_word = ?")
        params.append(new_source)
    if new_translation:
        updates.append("translation = ?")
        params.append(new_translation)
    if new_example:
        updates.append("example = ?")
        params.append(new_example)
    if new_transcription:
        updates.append("transcription = ?")
        params.append(new_transcription)
    if new_tags:
        updates.append("tags = ?")
        params.append(new_tags)
    
    if not updates:
        print("Ничего не изменено")
        conn.close()
        return
    
    params.append(word_id)
    query = f"UPDATE words SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    logging.info(f"Отредактировано слово id={word_id}")
    print("✅ Слово обновлено")

def delete_word():
    """Удаление карточки слова"""
    word_id = input("\nВведите ID слова для удаления: ").strip()
    if not word_id.isdigit():
        print("Ошибка: ID должен быть числом")
        return
    
    confirm = input(f"Удалить слово? (да/нет): ").strip().lower()
    if confirm != "да":
        print("Отменено")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE id = ?", (word_id,))
    cursor.execute("DELETE FROM review_stats WHERE word_id = ?", (word_id,))
    conn.commit()
    conn.close()
    
    logging.info(f"Удалено слово id={word_id}")
    print("✅ Слово удалено")

# ------------------------- 2.2. Модуль тренажёра -------------------------
def get_words_for_quiz(limit=10):
    """Получение слов для викторины с учётом ошибок (спейсед репетишн)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Слова с большим количеством ошибок имеют больший вес
    cursor.execute('''
        SELECT w.id, w.source_word, w.translation, w.example, 
               COALESCE(rs.error_count, 0) as error_count
        FROM words w
        LEFT JOIN review_stats rs ON w.id = rs.word_id
        ORDER BY error_count DESC, RANDOM()
        LIMIT ?
    ''', (limit,))
    words = cursor.fetchall()
    conn.close()
    return words

def update_error_count(word_id, is_correct):
    """Обновление счётчика ошибок"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if not is_correct:
        cursor.execute('''
            UPDATE review_stats 
            SET error_count = error_count + 1, last_reviewed = ?
            WHERE word_id = ?
        ''', (get_date(), word_id))
    else:
        cursor.execute('''
            UPDATE review_stats 
            SET last_reviewed = ?
            WHERE word_id = ?
        ''', (get_date(), word_id))
    
    conn.commit()
    conn.close()

def quiz_translation_to_native():
    """Упражнение: перевод с иностранного на родной"""
    words = get_words_for_quiz(8)
    if not words:
        print("\n📭 Словарь пуст. Добавьте слова сначала.")
        return
    
    correct = 0
    total = len(words)
    
    print("\n" + "="*50)
    print("УПРАЖНЕНИЕ: Переведите слово на русский")
    print("="*50)
    
    for word in words:
        print(f"\nСлово: {word[1]}")
        if word[3]:
            print(f"Пример: {word[3]}")
        
        answer = input("Ваш перевод: ").strip().lower()
        if answer == word[2].lower():
            print("✅ Правильно!")
            correct += 1
            update_error_count(word[0], True)
        else:
            print(f"❌ Неправильно. Правильный перевод: {word[2]}")
            update_error_count(word[0], False)
    
    percent = (correct / total) * 100
    print("\n" + "="*50)
    print(f"РЕЗУЛЬТАТ: {correct}/{total} ({percent:.1f}%)")
    print("="*50)
    logging.info(f"Тренировка завершена: {correct}/{total}")

def quiz_native_to_translation():
    """Упражнение: перевод с родного на иностранный"""
    words = get_words_for_quiz(8)
    if not words:
        print("\n📭 Словарь пуст. Добавьте слова сначала.")
        return
    
    correct = 0
    total = len(words)
    
    print("\n" + "="*50)
    print("УПРАЖНЕНИЕ: Переведите на иностранный язык")
    print("="*50)
    
    for word in words:
        print(f"\nПеревод слова: {word[2]}")
        
        answer = input("Ваш вариант: ").strip().lower()
        if answer == word[1].lower():
            print("✅ Правильно!")
            correct += 1
            update_error_count(word[0], True)
        else:
            print(f"❌ Неправильно. Правильный ответ: {word[1]}")
            update_error_count(word[0], False)
    
    percent = (correct / total) * 100
    print("\n" + "="*50)
    print(f"РЕЗУЛЬТАТ: {correct}/{total} ({percent:.1f}%)")
    print("="*50)
    logging.info(f"Тренировка завершена: {correct}/{total}")

def quiz_multiple_choice():
    """Упражнение: выбор правильного варианта из 4"""
    words = get_words_for_quiz(6)
    if not words:
        print("\n📭 Словарь пуст. Добавьте слова сначала.")
        return
    
    correct = 0
    total = len(words)
    
    print("\n" + "="*50)
    print("УПРАЖНЕНИЕ: Выберите правильный перевод")
    print("="*50)
    
    for word in words:
        # Получаем 3 случайных неправильных варианта
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT translation FROM words WHERE id != ? ORDER BY RANDOM() LIMIT 3", (word[0],))
        wrong_options = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        options = [word[2]] + wrong_options
        random.shuffle(options)
        
        print(f"\nСлово: {word[1]}")
        for i, opt in enumerate(options, 1):
            print(f"   {i}. {opt}")
        
        try:
            choice = int(input("Ваш выбор (1-4): "))
            if 1 <= choice <= 4 and options[choice-1] == word[2]:
                print("✅ Правильно!")
                correct += 1
                update_error_count(word[0], True)
            else:
                print(f"❌ Неправильно. Правильный ответ: {word[2]}")
                update_error_count(word[0], False)
        except ValueError:
            print(f"❌ Неправильно. Правильный ответ: {word[2]}")
            update_error_count(word[0], False)
    
    percent = (correct / total) * 100
    print("\n" + "="*50)
    print(f"РЕЗУЛЬТАТ: {correct}/{total} ({percent:.1f}%)")
    print("="*50)
    logging.info(f"Тренировка завершена: {correct}/{total}")

def start_quiz():
    """Главное меню тренажёра"""
    print("\n--- РЕЖИМ ТРЕНАЖЁРА ---")
    print("1. Перевод с иностранного на русский")
    print("2. Перевод с русского на иностранный")
    print("3. Выбор правильного варианта")
    print("0. Назад")
    
    choice = input("Выберите тип упражнения: ").strip()
    
    if choice == "1":
        quiz_translation_to_native()
    elif choice == "2":
        quiz_native_to_translation()
    elif choice == "3":
        quiz_multiple_choice()
    elif choice == "0":
        return
    else:
        print("Неверный ввод")

# ------------------------- 2.3. Модуль управления данными -------------------------
def export_to_csv():
    """Экспорт словаря в CSV"""
    filename = f"lingua_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_word, translation, example, tags FROM words")
    words = cursor.fetchall()
    conn.close()
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["слово", "перевод", "пример", "теги"])
        writer.writerows(words)
    
    print(f"✅ Экспортировано в {filename}")
    logging.info(f"Экспорт CSV: {filename}")

def export_to_zip():
    """Экспорт всех данных в ZIP-архив"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"lingua_export_{timestamp}.zip"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM words")
    words = cursor.fetchall()
    conn.close()
    
    # Подготовка JSON
    words_list = []
    for w in words:
        words_list.append({
            "id": w[0],
            "source_word": w[1],
            "translation": w[2],
            "example": w[3],
            "transcription": w[4],
            "tags": w[5],
            "added_date": w[6]
        })
    
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        # JSON
        zipf.writestr("words.json", json.dumps(words_list, ensure_ascii=False, indent=2))
        # CSV
        csv_content = "source_word,translation,example,tags\n"
        for w in words:
            csv_content += f"{w[1]},{w[2]},{w[3] if w[3] else ''},{w[5] if w[5] else ''}\n"
        zipf.writestr("words.csv", csv_content)
        # База данных
        zipf.write(DB_PATH, "backup.sqlite")
    
    print(f"✅ Экспортировано в {zip_name}")
    logging.info(f"Экспорт ZIP: {zip_name}")

def backup_db():
    """Создание резервной копии БД"""
    Path("backups").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backups/backup_{timestamp}.sqlite"
    shutil.copy2(DB_PATH, backup_name)
    print(f"✅ Резервная копия: {backup_name}")
    logging.info(f"Backup: {backup_name}")

# ------------------------- Функции высшего порядка (для демонстрации) -------------------------
def create_tag_filter(tag):
    """Замыкание: фабрика фильтров по тегу"""
    return lambda word: tag in word[4] if word[4] else False

def demo_functional_features():
    """Демонстрация filter, map, lambda, замыкания"""
    print("\n--- ДЕМОНСТРАЦИЯ ФУНКЦИОНАЛЬНЫХ КОНСТРУКЦИЙ ---")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, source_word, translation, tags FROM words")
    words = cursor.fetchall()
    conn.close()
    
    if not words:
        print("Нет слов для демонстрации")
        return
    
    # 1. filter + lambda: слова с тегом "еда"
    tag_filter = create_tag_filter("еда")
    food_words = list(filter(tag_filter, words))
    print(f"\n1. Слова с тегом 'еда': {[w[1] for w in food_words]}")
    
    # 2. map: извлечение только исходных слов
    source_words = list(map(lambda w: w[1], words))
    print(f"2. Все исходные слова: {source_words}")
    
    # 3. sorted с lambda: сортировка по слову
    sorted_words = sorted(words, key=lambda w: w[1])
    print(f"3. Слова по алфавиту: {[w[1] for w in sorted_words]}")

# ------------------------- Главное меню -------------------------
def main_menu():
    while True:
        print("\n" + "="*50)
        print("         LINGUALOG - Языковой тренажёр")
        print("="*50)
        print("1.  Добавить слово")
        print("2.  Список слов")
        print("3.  Просмотреть слово")
        print("4.  Редактировать слово")
        print("5.  Удалить слово")
        print("6.  Тренажёр")
        print("7.  Экспорт в CSV")
        print("8.  Экспорт в ZIP")
        print("9.  Резервное копирование")
        print("10. Демонстрация filter/map/lambda")
        print("0.  Выход")
        print("-"*50)
        
        choice = input("Ваш выбор: ").strip()
        
        if choice == "1":
            add_word()
        elif choice == "2":
            list_words()
        elif choice == "3":
            view_word()
        elif choice == "4":
            edit_word()
        elif choice == "5":
            delete_word()
        elif choice == "6":
            start_quiz()
        elif choice == "7":
            export_to_csv()
        elif choice == "8":
            export_to_zip()
        elif choice == "9":
            backup_db()
        elif choice == "10":
            demo_functional_features()
        elif choice == "0":
            print("\nДо свидания! Учите языки с удовольствием! 📚")
            logging.info("Приложение завершено")
            break
        else:
            print("Неверный ввод")

# ------------------------- Запуск -------------------------
if __name__ == "__main__":
    init_db()
    main_menu()