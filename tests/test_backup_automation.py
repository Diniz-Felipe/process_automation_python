import os
import shutil
from unittest.mock import MagicMock, patch
from datetime import datetime
import pytest

from app.backup_automation import (
    perform_backup, 
    save_backup_info_to_mongodb,
    restore_backup, 
    compress_backup, encrypt_backup, decrypt_backup,
    log_start_backup, log_error, log_end_backup, send_email_notification
)

@pytest.fixture
def mongodb_connection():
    return MagicMock()

@pytest.fixture
def base_test_directory():
    return os.path.abspath(r'path\to\tests') # Diretório em questão

@pytest.fixture
def source_directory(base_test_directory):
    return os.path.join(base_test_directory, 'source')

@pytest.fixture
def destination_directory(base_test_directory):
    return os.path.join(base_test_directory, 'destination')

@pytest.fixture
def private_key(base_test_directory):
    return os.path.join(base_test_directory, 'key.gpg')

@pytest.fixture
def log_file_path():
    return 'backup_log_test.txt'

def test_save_backup_info_to_mongodb(mongodb_connection):
    # Criar dados simulados para backup_info
    backup_info = {
        'source_directory': r'path\to\tests\source', # Substituir com o valor correto do diretório
        'destination_directory': r'path\to\tests\destination', # Substituir com o valor correto do diretório
        'backup_folder': r'path\to\tests\backup_folder', # Substituir com o valor correto do diretório
        'backup_directory': 'backup_20231220_105831_v1'  # Substituir com o valor correto
    }

    # Chamar a função que você deseja testar
    save_backup_info_to_mongodb(backup_info, mongodb_connection)
    
    mongodb_connection.backup_info.insert_one.assert_called_once_with(backup_info)

def test_perform_backup(source_directory, destination_directory, mongodb_connection):
    # Configurar um ambiente de teste com um diretório de origem vazio
    os.makedirs(source_directory)

    # Backup anterior para simular a existência do diretório de backup
    previous_backup_folder = os.path.join(destination_directory, 'backup_20231220_095619')
    os.makedirs(previous_backup_folder)

    # Chamar a função que você deseja testar
    perform_backup(source_directory, destination_directory, mongodb_connection)

    # Asserções para verificar se o backup foi realizado com sucesso
    assert os.path.exists(destination_directory)
    mongodb_connection.backup_info.insert_one.assert_called_once()

def test_compress_backup(source_directory, destination_directory):
    # Configurar um ambiente de teste com um backup prévio
    shutil.copytree(source_directory, destination_directory)

    # Chamar a função que você deseja testar
    compress_backup(destination_directory)

    # Adicione asserções para verificar se o backup foi compactado corretamente
    assert os.path.exists(f"{destination_directory}.zip")
    assert not os.path.exists(destination_directory)

def test_encrypt_decrypt_backup(source_directory, destination_directory, private_key):
    # Configurar um ambiente de teste com um backup prévio
    shutil.copytree(source_directory, destination_directory)

    # Chamar a função que você deseja testar
    encrypt_backup(destination_directory, private_key)

    # Adicione asserções para verificar se o backup foi criptografado/descriptografado corretamente
    assert all(file.endswith('.gpg') for file in os.listdir(destination_directory))

    # Descriptografar backup
    decrypt_backup(destination_directory, private_key)

    # Verificar se o backup foi descriptografado com sucesso
    assert all(not file.endswith('.gpg') for file in os.listdir(destination_directory))

def test_restore_backup(source_directory, destination_directory, mongodb_connection, private_key):
    # Configura um ambiente de teste com um backup prévio
    shutil.copytree(source_directory, destination_directory)

    # Realiza backup
    perform_backup(source_directory, destination_directory, mongodb_connection)

    # Obter a versão do backup
    version = mongodb_connection.backup_info.find_one()['datetime']

    # Chamar a função que você deseja testar
    restore_backup(version, mongodb_connection, private_key)

    # Verificar se a restauração foi bem-sucedida
    assert os.path.exists(source_directory)

def test_log_start_backup(log_file_path):
    # Chamar a função que você deseja testar
    log_start_backup("Backup started at 20231220_105831", log_file_path)

    # Verificar se a entrada foi adicionada corretamente ao arquivo de log
    with open(log_file_path, 'r', encoding='utf-8') as log_file:
        log_content = log_file.read()
        assert "Backup started at 20231220_105831" in log_content

def test_log_error(log_file_path):

    log_error("Error during backup: File not found", log_file_path)

    # Verificar se a entrada foi adicionada corretamente ao arquivo de log
    with open(log_file_path, 'r', encoding='utf-8') as log_file:
        log_content = log_file.read()
        assert "Error during backup: File not found" in log_content

def test_log_end_backup(log_file_path):
    # Chamar a função que você deseja testar
    log_end_backup("Backup completed at 20231220_110000", log_file_path)

    # Verificar se a entrada foi adicionada corretamente ao arquivo de log
    with open(log_file_path, 'r', encoding='utf-8') as log_file:
        log_content = log_file.read()
        assert "Backup completed at 20231220_110000" in log_content

def test_send_email_notification():
    # teste para o envio de e-mail
    with patch('smtplib.SMTP') as mock_smtp:
        send_email_notification("Test email")

    # Verifica se o método `sendmail` foi chamado
    mock_smtp.return_value.sendmail.assert_called_once()