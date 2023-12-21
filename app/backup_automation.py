import shutil
import os
from datetime import datetime
from pymongo import MongoClient
import smtplib
import email.message
import zipfile
import gnupg
import json
import logging

LOG_FILE = 'backup_log.txt'
TEMP_FOLDER_PREFIX = 'temp_restore'

def save_backup_info_to_mongodb(backup_info, mongodb_connection):
    """
    Salva as informações do backup no MongoDB.
    """
    mongodb_connection.backup_info.insert_one(json.loads(json.dumps(backup_info, default=str)))

def perform_backup(source_directory, destination_directory, mongodb_connection):
    try:
        current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_folder = os.path.join(destination_directory, f'backup_{current_datetime}')

        # verifica se existe uma versão, e adiona a próxima.
        backup_index = 1
        while True:
            backup_folder = os.path.join(destination_directory, f'backup_{current_datetime}_v{backup_index}')
            if not os.path.exists(backup_folder):
                os.makedirs(backup_folder)
                break
            backup_index += 1

        log_start_backup(f"Backup started at {current_datetime}")

        shutil.copytree(source_directory, backup_folder)

        compress_backup(backup_folder)

        # Não é uma chave veridica pórem para testes.
        private_key = '3909305fnjruihfg' 

        if 'private_key' in locals():
            encrypt_backup(backup_folder, private_key)

        log_end_backup(f"Backup completed at {datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Convert data to JSON before inserting into MongoDB
        backup_info = {
            'datetime': current_datetime,
            'source_directory': source_directory,
            'destination_directory': destination_directory,
            'backup_folder': backup_folder,
            'backup_directory': os.path.basename(backup_folder)  # Adicionando o diretório ao backup_info
        }

        # Insert into MongoDB
        save_backup_info_to_mongodb(backup_info, mongodb_connection)

        logging.info(f"Backup completed successfully at: {backup_folder}")

    except FileNotFoundError as e:
        log_error(f"Arquivo não encontrado: {e}")
    except PermissionError as e:
        log_error(f"Erro de permissão: {e}")
    except shutil.Error as e:
        log_error(f"Erro durante a operação shutil: {e}")
    except Exception as e:
        log_error(f"Erro inesperado: {e}")

        send_email_notification(f"Error during backup: {e}")

def compress_backup(backup_folder):
    with zipfile.ZipFile(f"{backup_folder}.zip", 'w') as zip_file:
        for root, _, files in os.walk(backup_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, backup_folder)
                zip_file.write(file_path, arcname=arcname)

    shutil.rmtree(backup_folder)

def encrypt_backup(backup_folder, private_key):
    gpg = gnupg.GPG()
    with open(private_key, 'r') as key_file:
        key = gpg.import_keys(key_file.read())

    for root, _, files in os.walk(backup_folder):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                encrypted_file = gpg.encrypt_file(f, recipients=[key.fingerprints[0]], output=f"{file_path}.gpg")
            os.remove(file_path)

def decrypt_backup(backup_folder, private_key_file):
    gpg = gnupg.GPG()
    with open(private_key_file, 'r') as key_file:
        gpg.decrypt_file(backup_folder)

def extract_backup(zip_file, destination_folder):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(destination_folder)

def restore_backup(version, mongodb_connection, private_key):
    try:
        backup_info = mongodb_connection.backup_info.find_one({'datetime': version})
        temporary_folder = f"{TEMP_FOLDER_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(temporary_folder)

        extract_backup(backup_info['backup_folder'], temporary_folder)

        if private_key:
            decrypt_backup(temporary_folder, private_key)

        restore_files(temporary_folder, backup_info['source_directory'])

        shutil.rmtree(temporary_folder)

        logging.info(f"Restoration completed successfully for version {version}")
        

    except FileNotFoundError as e:
        log_error(f"Arquivo não encontrado: {e}")
    except PermissionError as e:
        log_error(f"Erro de permissão: {e}")
    except shutil.Error as e:
        log_error(f"Erro durante a operação shutil: {e}")
    except Exception as e:
        log_error(f"Erro inesperado: {e}")

def restore_files(source_folder, destination_folder):
    shutil.copytree(source_folder, destination_folder)

def log_start_backup(message):
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}: {message}\n")

def log_end_backup(message):
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}: {message}\n")

def log_error(message):
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}: Error - {message}\n")

def send_email_notification(message):
    msg = email.message.Message()
    msg['Subject'] = "Subject" # Credencias á desejar testar
    msg['From'] = "sender" # Credencias á desejar testar
    msg['To'] = 'recipient' # Credencias á desejar testar
    password = 'password' # Credencias á desejar testar
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(message)

     # Configurando o servidor SMTP
    s = smtplib.SMTP('smtp.gmail.com:587')
    s.starttls()
    s.login(msg['From'], password)
    s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
    print('Email sent successfully')
