import pytest
import os
from PIL import Image

from main import (
    xor_cipher,
    add_watermark,
    add_qr,
    stego_hide,
    stego_extract
)


@pytest.fixture
def temp_files():
    input_file = 'test_source.png'
    output_file = 'test_result.png'

    img = Image.new('RGB', (100, 100), color='red')
    img.save(input_file)

    yield input_file, output_file

    if os.path.exists(input_file):
        os.remove(input_file)
    if os.path.exists(output_file):
        os.remove(output_file)


def test_xor_cipher_positive():
    """
    Проверка успешного шифрования и дешифровки.
    """
    original = b'Secret Data'
    password = 'super_pass'

    encrypted = xor_cipher(original, password)
    decrypted = xor_cipher(encrypted, password)

    assert original == decrypted
    assert encrypted != original


def test_xor_cipher_no_password():
    """
    Если пароль пустой, данные не должны меняться.
    """
    original = b'Data'
    result = xor_cipher(original, '')
    assert result == original


def test_text_watermark_positive(temp_files):
    """
    Проверка, что файл создается.
    """
    in_p, out_p = temp_files
    add_watermark(in_p, out_p, 'Test', 10, 10, 128)
    assert os.path.exists(out_p)


def test_text_watermark_negative_opacity(temp_files):
    """
    Проверка ошибки при неверной прозрачности (больше 255).
    """
    in_p, out_p = temp_files
    with pytest.raises(ValueError):
        add_watermark(in_p, out_p, 'Test', 10, 10, 300)


def test_qr_watermark_positive(temp_files):
    """
    Проверка создания QR кода.
    """
    in_p, out_p = temp_files
    add_qr(in_p, out_p, 'http://test.com', 10, 10, 255, 'black')
    assert os.path.exists(out_p)


def test_qr_watermark_negative_opacity(temp_files):
    """
    Проверка ошибки при отрицательной прозрачности.
    """
    in_p, out_p = temp_files
    with pytest.raises(ValueError):
        add_qr(in_p, out_p, 'Data', 0, 0, -50, 'black')


def test_steganography_positive(temp_files):
    in_p, out_p = temp_files
    secret = 'Секретный прикол'
    password = '123'

    stego_hide(in_p, out_p, secret, password)
    extracted = stego_extract(out_p, password)

    assert extracted == secret


def test_steganography_negative_capacity(temp_files):
    """
    Проверка переполнения: текст больше картинки.
    """
    in_p, out_p = temp_files
    huge_text = 'A' * 15000

    with pytest.raises(ValueError):
        stego_hide(in_p, out_p, huge_text)
