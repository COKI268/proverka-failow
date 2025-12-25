import hashlib
import os
import json
from datetime import datetime
import sys

def calculate_hash(file_path, algorithm='sha256'):
    """
    Вычисляет хеш-сумму файла с использованием указанного алгоритма
    
    Args:
        file_path: путь к файлу
        algorithm: алгоритм хеширования ('md5', 'sha1', 'sha256')
    
    Returns:
        str: хеш-сумма файла в шестнадцатеричном формате
    
    Raises:
        FileNotFoundError: если файл не существует
        IOError: если ошибка чтения файла
    """
    # Создаем объект хеша в зависимости от выбранного алгоритма
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Неподдерживаемый алгоритм: {algorithm}")
    
    try:
        # Открываем файл в бинарном режиме для чтения
        with open(file_path, 'rb') as file:
            # Читаем файл блоками для эффективной обработки больших файлов
            block_size = 65536  # 64KB блоки
            
            # Читаем первый блок
            chunk = file.read(block_size)
            
            # Пока есть данные, обновляем хеш
            while chunk:
                hash_obj.update(chunk)
                chunk = file.read(block_size)
        
        # Возвращаем хеш в виде шестнадцатеричной строки
        return hash_obj.hexdigest()
    
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден: {file_path}")
        raise
    except IOError as e:
        print(f"Ошибка чтения файла {file_path}: {e}")
        raise

def create_checksum_file(directory_path, output_file='checksums.json', algorithm='sha256'):
    """
    Создает файл с контрольными суммами для всех файлов в директории
    
    Args:
        directory_path: путь к директории
        output_file: имя выходного файла
        algorithm: алгоритм хеширования
    """
    checksums = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'algorithm': algorithm,
            'directory': directory_path
        },
        'files': {}
    }
    
    try:
        # Проверяем существование директории
        if not os.path.exists(directory_path):
            print(f"Ошибка: Директория не существует: {directory_path}")
            return False
        
        print(f"Сканирование директории: {directory_path}")
        print("-" * 50)
        
        # Получаем список всех файлов в директории и поддиректориях
        file_count = 0
        
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                
                # Пропускаем сам файл checksums, если он существует
                if file_name == output_file:
                    print(f"Пропускаем файл с контрольными суммами: {file_name}")
                    continue
                
                try:
                    # Вычисляем хеш для файла
                    file_hash = calculate_hash(file_path, algorithm)
                    
                    # Сохраняем относительный путь для удобства
                    rel_path = os.path.relpath(file_path, directory_path)
                    
                    checksums['files'][rel_path] = {
                        'hash': file_hash,
                        'size': os.path.getsize(file_path),
                        'modified': os.path.getmtime(file_path)
                    }
                    
                    print(f" Обработан: {rel_path}")
                    file_count += 1
                    
                except Exception as e:
                    print(f" Ошибка при обработке {file_path}: {e}")
        
        # Сохраняем результаты в JSON файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(checksums, f, indent=2, ensure_ascii=False)
        
        print("-" * 50)
        print(f"Готово! Обработано файлов: {file_count}")
        print(f"Контрольные суммы сохранены в: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return False

def verify_integrity(checksum_file, directory_path=None):
    """
    Проверяет целостность файлов с использованием файла контрольных сумм
    
    Args:
        checksum_file: путь к файлу с контрольными суммами
        directory_path: путь к директории для проверки (если None, берется из checksum_file)
    """
    try:
        # Загружаем данные контрольных сумм
        with open(checksum_file, 'r', encoding='utf-8') as f:
            checksums = json.load(f)
        
        algorithm = checksums['metadata']['algorithm']
        original_dir = checksums['metadata']['directory']
        
        # Если directory_path не указан, используем из файла
        if directory_path is None:
            directory_path = original_dir
        
        print(f"Проверка целостности файлов в: {directory_path}")
        print(f"Используется алгоритм: {algorithm}")
        print("-" * 50)
        
        verification_results = {
            'passed': 0,
            'failed': 0,
            'missing': 0,
            'total': len(checksums['files'])
        }
        
        # Проверяем каждый файл из контрольных сумм
        for rel_path, file_info in checksums['files'].items():
            file_path = os.path.join(directory_path, rel_path)
            
            if os.path.exists(file_path):
                try:
                    # Вычисляем текущий хеш файла
                    current_hash = calculate_hash(file_path, algorithm)
                    original_hash = file_info['hash']
                    
                    # Сравниваем хеши
                    if current_hash == original_hash:
                        print(f" Целостность подтверждена: {rel_path}")
                        verification_results['passed'] += 1
                    else:
                        print(f" НАРУШЕНА ЦЕЛОСТНОСТЬ: {rel_path}")
                        print(f"  Ожидалось: {original_hash}")
                        print(f"  Получено:  {current_hash}")
                        verification_results['failed'] += 1
                        
                except Exception as e:
                    print(f" Ошибка при проверке {rel_path}: {e}")
                    verification_results['failed'] += 1
            else:
                print(f" Файл отсутствует: {rel_path}")
                verification_results['missing'] += 1
        
        # Выводим сводку проверки
        print("-" * 50)
        print("РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
        print(f"Всего файлов для проверки: {verification_results['total']}")
        print(f" Целостность подтверждена: {verification_results['passed']}")
        print(f" Нарушена целостность: {verification_results['failed']}")
        print(f" Отсутствуют файлы: {verification_results['missing']}")
        
        if verification_results['failed'] == 0 and verification_results['missing'] == 0:
            print("\n Все файлы целы и невредимы!")
            return True
        else:
            print("\n Обнаружены проблемы с целостностью файлов!")
            return False
            
    except FileNotFoundError:
        print(f"Ошибка: Файл с контрольными суммами не найден: {checksum_file}")
        return False
    except json.JSONDecodeError:
        print(f"Ошибка: Некорректный формат JSON в файле: {checksum_file}")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка при проверке: {e}")
        return False

def show_menu():
    """Отображает меню программы"""
    print("\n" + "="*50)
    print("ПРОГРАММА ПРОВЕРКИ ЦЕЛОСТНОСТИ ФАЙЛОВ")
    print("="*50)
    print("1. Создать контрольные суммы для директории")
    print("2. Проверить целостность файлов")
    print("3. Проверить один файл")
    print("4. Выход")
    print("-"*50)
    
    choice = input("Выберите действие (1-4): ").strip()
    return choice

def check_single_file():
    """Проверяет целостность одного файла"""
    file_path = input("Введите путь к файлу: ").strip()
    
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return
    
    print("\nДоступные алгоритмы хеширования:")
    print("1. MD5")
    print("2. SHA-1")
    print("3. SHA-256 (рекомендуется)")
    
    algo_choice = input("Выберите алгоритм (1-3): ").strip()
    
    if algo_choice == '1':
        algorithm = 'md5'
    elif algo_choice == '2':
        algorithm = 'sha1'
    else:
        algorithm = 'sha256'
    
    try:
        file_hash = calculate_hash(file_path, algorithm)
        file_size = os.path.getsize(file_path)
        
        print("\n" + "="*50)
        print(f"Файл: {file_path}")
        print(f"Размер: {file_size} байт")
        print(f"Алгоритм: {algorithm.upper()}")
        print(f"Хеш-сумма: {file_hash}")
        print("="*50)
        
        # Предлагаем сравнить с известной хеш-суммой
        compare = input("\nСравнить с известной хеш-суммой? (y/n): ").strip().lower()
        if compare == 'y':
            known_hash = input("Введите известную хеш-сумму: ").strip()
            if file_hash == known_hash:
                print(" Хеш-суммы совпадают! Файл цел.")
            else:
                print(" Хеш-суммы НЕ совпадают! Возможно файл изменен.")
                
    except Exception as e:
        print(f"Ошибка: {e}")

def main():
    """Основная функция программы"""
    print("Добро пожаловать в программу проверки целостности файлов!")
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            # Создание контрольных сумм
            directory = input("Введите путь к директории: ").strip()
            output = input("Введите имя файла для сохранения (по умолчанию: checksums.json): ").strip()
            if not output:
                output = 'checksums.json'
            
            print("\nДоступные алгоритмы хеширования:")
            print("1. MD5 (быстрый, но менее безопасный)")
            print("2. SHA-1 (устаревший)")
            print("3. SHA-256 (рекомендуется)")
            
            algo_choice = input("Выберите алгоритм (1-3): ").strip()
            
            if algo_choice == '1':
                algorithm = 'md5'
            elif algo_choice == '2':
                algorithm = 'sha1'
            else:
                algorithm = 'sha256'
            
            create_checksum_file(directory, output, algorithm)
            
        elif choice == '2':
            # Проверка целостности
            checksum_file = input("Введите путь к файлу с контрольными суммами: ").strip()
            directory = input("Введите путь к директории для проверки (Enter для пути из файла): ").strip()
            
            if directory:
                verify_integrity(checksum_file, directory)
            else:
                verify_integrity(checksum_file)
                
        elif choice == '3':
            # Проверка одного файла
            check_single_file()
            
        elif choice == '4':
            # Выход
            print("Спасибо за использование программы! До свидания!")
            break
            
        else:
            print("Неверный выбор. Пожалуйста, выберите действие от 1 до 4.")
        
        input("\nНажмите Enter для продолжения...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем.")
        sys.exit(0)
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        sys.exit(1)
