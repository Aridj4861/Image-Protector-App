import argparse
import sys
import os
import hashlib
from itertools import cycle
from PIL import Image, ImageDraw, ImageFont
import qrcode


def get_hash(file_path):
    """
    Вычисляет SHA-256 хеш файла для проверки целостности.

    Считывает файл блоками по 4096 байт, чтобы не нагружать оперативную
    память при работе с большими изображениями.

    Args:
        file_path (str): Путь к файлу, хеш которого нужно получить.

    Returns:
        sha256 (str): Хеш-сумма файла в шестнадцатеричном формате.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b''):
            sha256_hash.update(byte_block)
            sha256 = sha256_hash.hexdigest()
    return sha256


def xor_cipher(data, password):
    """
    Шифрует или дешифрует байты с помощью операции XOR.

    Args:
        data (bytes): Входные данные (байтовая строка).
        password (str): Пароль для шифрования/дешифрования.

    Returns:
        bytes: Результат операции XOR.
    """
    if not password:
        return data
    key = password.encode('utf-8')
    return bytes([a ^ b for a, b in zip(data, cycle(key))])


def bytes_to_bits(data):
    """
    Преобразует последовательность байтов в список битов.

    Каждый байт преобразуется в 8 битов (0 или 1).

    Args:
        data (bytes): Входные байтовые данные.

    Returns:
        list: Список целых чисел (0 и 1), представляющий биты данных.
    """
    bits = []
    for byte in data:
        bin_val = format(byte, '08b')
        bits.extend([int(b) for b in bin_val])
    return bits


def bits_to_bytes(bits):
    """
    Собирает список битов обратно в последовательность байтов.

    Группирует биты по 8 штук и преобразует их в соответствующие
    байтовые значения.

    Args:
        bits (list): Список целых чисел (0 и 1).

    Returns:
        bytes: Восстановленная байтовая строка.
    """
    byte_values = []
    for i in range(0, len(bits), 8):
        byte_chunk = bits[i:i + 8]
        if len(byte_chunk) < 8:
            break
        byte_val = int(''.join(map(str, byte_chunk)), 2)
        byte_values.append(byte_val)
    return bytes(byte_values)


def get_files_list(input_path, output_path):
    """
    Формирует список задач для обработки файлов.

    Если указана папка, составляет список всех изображений внутри неё.
    Если указан файл, возвращает список из одного элемента.

    Args:
        input_path (str): Путь к исходному файлу или папке.
        output_path (str): Путь для сохранения результата (файл или папка).

    Returns:
        list: Список кортежей вида [(входной_путь, выходной_путь), ...].
    """
    tasks = []
    if os.path.isdir(input_path):
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            print('Создана папка: ' + output_path)
        for filename in os.listdir(input_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                tasks.append((os.path.join(input_path, filename),
                              os.path.join(output_path, filename)))
    else:
        tasks.append((input_path, output_path))
    return tasks


def add_watermark(input_path, output_path, text, x, y, opacity):
    """
    Добавляет текстовый водяной знак на изображение.

    Args:
        input_path (str): Путь к исходному изображению.
        output_path (str): Путь для сохранения результата.
        text (str): Текст водяного знака.
        x (int): Координата X верхнего левого угла текста.
        y (int): Координата Y верхнего левого угла текста.
        opacity (int): Прозрачность текста (0 - полностью прозрачный, 255 - непрозрачный).

    Raises:
        ValueError: Если прозрачность вне диапазона 0-255.
        IOError: Если не удается открыть изображение или загрузить шрифт.
    """
    opacity = int(opacity)
    if not (0 <= opacity <= 255):
        raise ValueError('Прозрачность должна быть от 0 до 255')

    with Image.open(input_path).convert('RGBA') as base:
        txt_layer = Image.new('RGBA', base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        try:
            font = ImageFont.truetype('arial.ttf', 40)
        except IOError:
            font = ImageFont.load_default()

        draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
        out = Image.alpha_composite(base, txt_layer)

        if output_path.lower().endswith(('.jpg', '.jpeg')):
            out = out.convert('RGB')
        out.save(output_path)
        print('Текст добавлен, файл сохранён в: ' + output_path)


def add_qr(input_path, output_path, data, x, y, opacity, color='black'):
    """
    Генерирует QR-код и накладывает его на изображение.

    QR-код генерируется с прозрачным фоном. Цвет элементов кода
    можно выбрать (черный или белый).

    Args:
        input_path (str): Путь к исходному изображению.
        output_path (str): Путь для сохранения результата.
        data (str): Данные для кодирования в QR-код.
        x (int): Координата X для вставки QR-кода.
        y (int): Координата Y для вставки QR-кода.
        opacity (int): Прозрачность QR-кода (0-255).
        color (str): Цвет элементов QR-кода ('black' или 'white').

    Raises:
        ValueError: Если прозрачность вне диапазона 0-255.
    """
    opacity = int(opacity)
    if not (0 <= opacity <= 255):
        raise ValueError('Прозрачность должна быть от 0 до 255')

    qr_img = qrcode.make(data).convert('RGBA')
    pixels = qr_img.getdata()
    new_pixels = []

    for r, g, b, a in pixels:
        if r > 200:
            new_pixels.append((255, 255, 255, 0))
        else:
            if color == 'white':
                new_pixels.append((255, 255, 255, opacity))
            else:
                new_pixels.append((0, 0, 0, opacity))

    qr_img.putdata(new_pixels)

    with Image.open(input_path).convert('RGBA') as base:
        if qr_img.width > base.width:
            scale = base.width // 4
            qr_img = qr_img.resize((scale, scale))

        layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
        layer.paste(qr_img, (x, y))
        out = Image.alpha_composite(base, layer)

        if output_path.lower().endswith(('.jpg', '.jpeg')):
            out = out.convert('RGB')
        out.save(output_path)
        print('QR-код добавлен, файл сохранён в: ' + output_path)


def stego_hide(input_path, output_path, secret_text, password=''):
    """
    Скрывает текстовое сообщение в изображении методом LSB.

    Данные внедряются в младшие биты синего канала пикселей.
    Поддерживает опциональное шифрование XOR перед внедрением.

    Args:
        input_path (str): Путь к исходному изображению.
        output_path (str): Путь для сохранения изображения со скрытыми данными.
        secret_text (str): Текст, который нужно скрыть.
        password (str): Пароль для шифрования (опционально).

    Raises:
        ValueError: Если объем данных превышает емкость изображения.
    """
    data_bytes = secret_text.encode('utf-8')
    if password:
        data_bytes = xor_cipher(data_bytes, password)

    full_payload = data_bytes + b'$STOP$'
    bits = bytes_to_bits(full_payload)

    img = Image.open(input_path).convert('RGB')
    pixels = img.load()
    width, height = img.size
    idx = 0

    if len(bits) > width * height:
        raise ValueError('Слишком большие данные для этого изображения.')

    for y in range(height):
        for x in range(width):
            if idx < len(bits):
                r, g, b = pixels[x, y]
                new_b = (b & ~1) | bits[idx]
                pixels[x, y] = (r, g, new_b)
                idx += 1
            else:
                break
    img.save(output_path)
    print('Данные спрятаны, файл сохранён в: ' + output_path)


def stego_extract(input_path, password=''):
    """
    Извлекает скрытое сообщение из изображения.

    Считывает младшие биты синего канала до обнаружения стоп-слова.
    Если использовалось шифрование, расшифровывает данные.

    Args:
        input_path (str): Путь к изображению со скрытыми данными.
        password (str): Пароль для расшифровки (если использовался).

    Returns:
        str: Извлеченное сообщение или описание ошибки.
    """
    img = Image.open(input_path).convert('RGB')
    pixels = img.load()
    width, height = img.size

    extracted_bits = []
    max_bytes = 4096
    max_bits = max_bytes * 8
    bits_count = 0

    for y in range(height):
        if bits_count >= max_bits:
            break
        for x in range(width):
            if bits_count >= max_bits:
                break
            r, g, b = pixels[x, y]
            extracted_bits.append(b & 1)
            bits_count += 1

    raw_data = bits_to_bytes(extracted_bits)
    stop_marker = b'$STOP$'

    if stop_marker in raw_data:
        secret_bytes = raw_data.split(stop_marker)[0]
        if password:
            secret_bytes = xor_cipher(secret_bytes, password)
        try:
            return secret_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return 'Ошибка: Неправильный пароль или повреждённые данные.'
    else:
        return 'Не найдено скрытых данных.'


def clean_lsb(input_path, output_path):
    """
    Очищает изображение от скрытых LSB данных.

    Обнуляет младший бит синего канала у всех пикселей изображения.

    Args:
        input_path (str): Путь к исходному изображению.
        output_path (str): Путь для сохранения очищенного изображения.
    """
    img = Image.open(input_path).convert('RGB')
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            pixels[x, y] = (r, g, b & ~1)

    img.save(output_path)
    print('LSB-данные очищены, файл сохранён в: ' + output_path)


def interactive_mode():
    """
    Запускает интерактивный консольный интерфейс приложения.

    Позволяет пользователю выбирать команды из меню и вводить параметры
    пошагово. Работает в бесконечном цикле до выбора команды выхода.
    """
    print('=' * 40)
    print('СКРЕПНОЕ ПРИЛОЖЕНИЕ ДЛЯ ЗАЩИТЫ ИЗОБРАЖЕНИЙ')
    print('=' * 40)

    while True:
        print('\nВыберите действие:')
        print('1. Добавить текстовый водяной знак')
        print('2. Добавить QR-код как водяной знак')
        print('3. Спрятать послание через LSB')
        print('4. Извлечь послание через LSB')
        print('5. Уничтожить LSB-данные')
        print('6. Получить хэш файла')
        print('0. Выйти из программы')

        choice = input('\nВаш выбор > ')

        in_p = None
        out_p = None

        try:
            if choice == '0':
                break

            if choice in ['1', '2', '3', '4', '5', '6']:
                in_p = input('Путь к исходному файлу: ').strip('"').strip("'")
                if not os.path.exists(in_p):
                    print('Ошибка: Файл не найден')
                    continue

            if choice in ['1', '2', '3', '5']:
                out_p = input('Файл сохранится в: ').strip('"').strip("'")

            if choice == '1':
                txt = input('Text: ')
                op_in = input('Прозрачность (0-255, По умолчанию 128): ')
                op = int(op_in) if op_in else 128
                x_in = input('Отступ по X (По умолчанию 10): ')
                x = int(x_in) if x_in else 10
                y_in = input('Отступ по Y (По умолчанию 10): ')
                y = int(y_in) if y_in else 10

                tasks = get_files_list(in_p, out_p)
                for i, o in tasks:
                    add_watermark(i, o, txt, x, y, op)

            elif choice == '2':
                data = input('Данные для QR-кода: ')
                color = input('Цвет (black/white, По умолчанию black): ') or 'black'
                op_in = input('Прозрачность (0-255, По умолчанию 200): ')
                op = int(op_in) if op_in else 200
                x_in = input('X (По умолчанию 10): ')
                x = int(x_in) if x_in else 10
                y_in = input('Y (По умолчанию 10): ')
                y = int(y_in) if y_in else 10

                tasks = get_files_list(in_p, out_p)
                for i, o in tasks:
                    add_qr(i, o, data, x, y, op, color)

            elif choice == '3':
                sec = input('Секретное послание: ')
                pw = input('Пароль (опционально): ')
                stego_hide(in_p, out_p, sec, pw)

            elif choice == '4':
                pw = input('Пароль: ')
                print('\nРЕЗУЛЬТАТ: ' + stego_extract(in_p, pw))

            elif choice == '5':
                tasks = get_files_list(in_p, out_p)
                for i, o in tasks:
                    clean_lsb(i, o)

            elif choice == '6':
                print('SHA-256: ' + get_hash(in_p))

            else:
                print('Неверный выбор')

        except Exception as e:
            print('Возникла ошибка: ', e)


def main():
    """
    Точка входа в программу.

    Обрабатывает аргументы командной строки или запускает интерактивный
    режим, если аргументы не переданы.
    """
    if len(sys.argv) == 1:
        interactive_mode()
        return

    parser = argparse.ArgumentParser(description='Программа для защиты изображений')
    subparsers = parser.add_subparsers(dest='command', help='Список команд')

    cmd_text = subparsers.add_parser('text', help='Добавить текстовый водяной знак')
    cmd_text.add_argument('input', help='Путь к файлу или папке')
    cmd_text.add_argument('output', help='Путь для сохранения результата')
    cmd_text.add_argument('--text', required=True, help='Текст надписи')
    cmd_text.add_argument('--opacity', type=int, default=128, help='Прозрачность (0-255)')
    cmd_text.add_argument('--x', type=int, default=10, help='Отступ по X')
    cmd_text.add_argument('--y', type=int, default=10, help='Отступ по Y')

    cmd_qr = subparsers.add_parser('qr', help='Добавить QR-код')
    cmd_qr.add_argument('input', help='Путь к файлу или папке')
    cmd_qr.add_argument('output', help='Путь для сохранения результата')
    cmd_qr.add_argument('--data', required=True, help='Данные для шифрования в QR')
    cmd_qr.add_argument('--opacity', type=int, default=200, help='Прозрачность (0-255)')
    cmd_qr.add_argument('--x', type=int, default=10, help='Отступ по X')
    cmd_qr.add_argument('--y', type=int, default=10, help='Отступ по Y')
    cmd_qr.add_argument('--color', choices=['black', 'white'], default='black', help='Цвет QR-кода (black/white)')

    cmd_clean = subparsers.add_parser('clean', help='Очистить LSB-данные')
    cmd_clean.add_argument('input', help='Путь к файлу или папке')
    cmd_clean.add_argument('output', help='Путь для сохранения результата')

    cmd_hide = subparsers.add_parser('hide', help='Спрятать данные (LSB)')
    cmd_hide.add_argument('input', help='Исходный файл')
    cmd_hide.add_argument('output', help='Файл с секретом')
    cmd_hide.add_argument('--secret', required=True, help='Секретное сообщение')
    cmd_hide.add_argument('--password', default='', help='Пароль (необязательно)')

    cmd_extract = subparsers.add_parser('extract', help='Извлечь данные (LSB)')
    cmd_extract.add_argument('input', help='Файл с секретом')
    cmd_extract.add_argument('--password', default='', help='Пароль')

    cmd_hash = subparsers.add_parser('hash', help='Получить хеш файла')
    cmd_hash.add_argument('input', help='Файл для проверки')

    args = parser.parse_args()

    try:
        if args.command in ['text', 'qr', 'clean']:
            tasks = get_files_list(args.input, args.output)

            for in_path, out_path in tasks:
                try:
                    if args.command == 'text':
                        add_watermark(in_path, out_path, args.text,
                                      args.x, args.y, args.opacity)
                    elif args.command == 'qr':
                        add_qr(in_path, out_path, args.data,
                               args.x, args.y, args.opacity, args.color)
                    elif args.command == 'clean':
                        clean_lsb(in_path, out_path)
                except Exception as e:
                    print('Ошибка с файлом', in_path, ':', e)

        elif args.command == 'hide':
            stego_hide(args.input, args.output, args.secret, args.password)

        elif args.command == 'extract':
            msg = stego_extract(args.input, args.password)
            print('\nРЕЗУЛЬТАТ: ' + msg + '\n')

        elif args.command == 'hash':
            print('SHA-256: ' + get_hash(args.input))

        else:
            parser.print_help()

    except Exception as e:
        print('КРИТИЧЕСКАЯ ОШИБКА!!!! ЭТО КОНЕЦ И АПОКАЛИПСИС:', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
