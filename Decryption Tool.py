import os
import hashlib
import secrets
import base64

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import padding

SALT_SIZE = 16
IV_SIZE = 16
KEY_SIZE = 32
ITERATIONS = 100000
CHUNK_SIZE = 64 * 1024


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_file(input_filepath: str, output_filepath: str, password: str):
    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_key(password, salt)
    iv = secrets.token_bytes(IV_SIZE)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()

    try:
        with open(input_filepath, 'rb') as infile, open(output_filepath, 'wb') as outfile:
            outfile.write(salt)
            outfile.write(iv)

            while True:
                chunk = infile.read(CHUNK_SIZE)
                if len(chunk) == 0:
                    break

                padded_chunk = padder.update(chunk)
                ciphertext = encryptor.update(padded_chunk)
                outfile.write(ciphertext)

            remaining_padded = padder.finalize()
            remaining_ciphertext = encryptor.finalize()
            outfile.write(remaining_padded + remaining_ciphertext)

        print(f"File encrypted successfully: {output_filepath}")
        return True

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'")
        return False
    except Exception as e:
        print(f"An error occurred during encryption: {e}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return False


def decrypt_file(input_filepath: str, output_filepath: str, password: str):
    try:
        with open(input_filepath, 'rb') as infile, open(output_filepath, 'wb') as outfile:
            salt = infile.read(SALT_SIZE)
            if len(salt) != SALT_SIZE:
                print("Error: Could not read valid salt. File might be corrupted or not properly encrypted.")
                return False

            iv = infile.read(IV_SIZE)
            if len(iv) != IV_SIZE:
                print("Error: Could not read valid IV. File might be corrupted or not properly encrypted.")
                return False

            key = derive_key(password, salt)
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

            last_chunk = b''
            while True:
                chunk = infile.read(CHUNK_SIZE + algorithms.AES.block_size)
                if len(chunk) == 0:
                    break

                if len(chunk) < CHUNK_SIZE + algorithms.AES.block_size and infile.peek(1) == b'':
                    plaintext_chunk = decryptor.update(chunk)
                    try:
                        final_plaintext = unpadder.update(plaintext_chunk) + unpadder.finalize()
                        outfile.write(final_plaintext)
                    except ValueError as ve:
                        print(
                            f"Error: Padding verification failed. Incorrect password or corrupted file. Details: {ve}")
                        return False
                    last_chunk = b''
                    break
                else:
                    plaintext_chunk = decryptor.update(chunk)
                    outfile.write(plaintext_chunk)

            if last_chunk:
                try:
                    final_plaintext = unpadder.update(decryptor.finalize()) + unpadder.finalize()
                    outfile.write(final_plaintext)
                except ValueError as ve:
                    print(
                        f"Error: Padding verification failed on final chunk. Incorrect password or corrupted file. Details: {ve}")
                    return False

        print(f"File decrypted successfully: {output_filepath}")
        return True

    except FileNotFoundError:
        print(f"Error: Input encrypted file not found at '{input_filepath}'")
        return False
    except ValueError as ve:
        print(f"Decryption failed, likely incorrect password or corrupted file: {ve}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return False
    except Exception as e:
        print(f"An unexpected error occurred during decryption: {e}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return False


def main():
    print("--- Custom File Encryption/Decryption Tool ---")
    print("Choose an action:")
    print("1. Encrypt File")
    print("2. Decrypt File")

    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == '1':
        input_file = input("Enter the path to the file to encrypt: ").strip()
        output_file = input("Enter the desired output path for the encrypted file (e.g., myfile.aes): ").strip()
        password = input("Enter your encryption password: ").strip()

        if not input_file or not output_file or not password:
            print("All fields are required. Please try again.")
            return

        encrypt_file(input_file, output_file, password)

    elif choice == '2':
        input_file = input("Enter the path to the file to decrypt (e.g., myfile.aes): ").strip()
        output_file = input("Enter the desired output path for the decrypted file: ").strip()
        password = input("Enter your decryption password: ").strip()

        if not input_file or not output_file or not password:
            print("All fields are required. Please try again.")
            return

        decrypt_file(input_file, output_file, password)

    else:
        print("Invalid choice. Please enter '1' or '2'.")


if __name__ == "__main__":
    main()
