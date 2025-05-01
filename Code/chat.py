"""
Консольный чат на Python с использованием TCP сокетов.

Этот модуль реализует сервер и клиент для консольного чата. Сервер обрабатывает
подключения клиентов, пересылает сообщения и логирует события. Клиенты
подключаются к серверу, отправляют и получают сообщения.

Требования к функциональности:
    - Сервер:
        - Принимает подключения от клиентов по TCP порту.
        - Поддерживает минимум 2-х клиентов одновременно.
        - Доставляет сообщения адресату.
        - Сообщает отправителю об успехе или неудаче доставки.
        - Логирует события (сообщения от клиентов).
    - Клиенты:
        - Получают сообщения от сервера.
        - Отправляют сообщения.
        - Получают подтверждение о доставке.

Требования к реализации:
    - ОС: Oracle Linux 8.10
    - ЯП: Python 3.x (корректировка - Python 3.14 не существует)
    - Код: Документирован
    - Зависимости: Стандартная библиотека Python
    - Установка:  Не предусмотрена установка через RPM, так как это не типичная установка для Python скриптов.  Пример установки см. в разделе "Инструкция по установке".

Требования к документации:
    - Исходный код
    - Используемые модули/библиотеки
    - Инструкция по установке
    - Примеры использования
"""

import socket
import threading
import logging
import argparse
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("chat.log"),  # Запись логов в файл
        logging.StreamHandler(sys.stdout),  # Вывод логов в консоль
    ],
)
logger = logging.getLogger(__name__)

# Константы
HOST = "0.0.0.0"  # Слушаем на всех интерфейсах
PORT = 12345  # Порт для соединения
ENCODING = "utf-8"  # Кодировка сообщений
MAX_CLIENTS = 5  # Максимальное количество клиентов


class ClientHandler(threading.Thread):
    """
    Обработчик для каждого подключенного клиента.
    """

    def __init__(self, client_socket, client_address, server):
        """
        Инициализация обработчика клиента.

        Args:
            client_socket: Сокет клиента.
            client_address: Адрес клиента (IP, port).
            server: Ссылка на объект сервера.
        """
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.server = server
        self.username = None
        self.is_running = True  # Флаг для управления потоком
        self.client_socket.settimeout(60) # Установка таймаута сокета

    def run(self):
        """
        Основной цикл обработки сообщений от клиента.
        """
        try:
            self.username = self.get_username()
            if not self.username:
                self.close_connection()  # Если не удалось получить имя, закрываем соединение
                return

            self.server.broadcast(f"{self.username} присоединился к чату.", exclude=self)
            self.server.add_client(self)  # Добавляем клиента в список активных

            while self.is_running:
                try:
                    message = self.client_socket.recv(1024).decode(ENCODING)
                    if not message:
                        break  # Клиент отключился

                    self.handle_message(message)

                except socket.timeout:
                    logger.warning(f"Превышено время ожидания от {self.username}. Закрытие соединения.")
                    break # Прекращаем обработку клиента при таймауте сокета
                except (ConnectionResetError, OSError) as e:
                    logger.warning(f"Ошибка при получении сообщения от {self.username}: {e}")
                    break # Прекращаем обработку клиента при ошибке сокета

        finally:
            self.close_connection()

    def get_username(self):
        """
        Получает имя пользователя от клиента.

        Returns:
            str: Имя пользователя, или None если не удалось получить имя.
        """
        try:
            self.client_socket.send("Введите имя пользователя: ".encode(ENCODING))
            self.client_socket.settimeout(10) # Таймаут для получения имени пользователя
            username = self.client_socket.recv(1024).decode(ENCODING).strip()
            self.client_socket.settimeout(60) # Сбрасываем таймаут для дальнейшей работы
            if not username:
                self.client_socket.send("Имя пользователя не может быть пустым.\n".encode(ENCODING))
                return None
            if self.server.is_username_taken(username):
                self.client_socket.send("Это имя пользователя уже занято.\n".encode(ENCODING))
                return None
            return username
        except socket.timeout:
            self.client_socket.send("Превышено время ввода имени пользователя.\n".encode(ENCODING))
            logger.warning(f"Не удалось получить имя пользователя от {self.client_address} (таймаут)")
            return None #Возврат None при таймауте
        except (ConnectionResetError, OSError):
            logger.warning(f"Не удалось получить имя пользователя от {self.client_address}")
            return None

    def handle_message(self, message):
        """
        Обрабатывает полученное сообщение от клиента.

        Args:
            message (str): Текст сообщения.
        """
        if message.startswith("/to "):
            self.send_private_message(message)
        else:
            self.server.broadcast(f"[{self.username}]: {message}", exclude=self)
            logger.info(f"[{self.username}]: {message}") #логирование

    def send_private_message(self, message):
        """
        Отправляет личное сообщение другому клиенту.

        Args:
            message (str): Текст сообщения, начинающийся с "/to".
        """
        try:
            parts = message.split(" ", 2)
            if len(parts) < 3:
                self.client_socket.send("Неверный формат личного сообщения. Используйте /to <имя_получателя> <сообщение>\n".encode(ENCODING))
                return

            recipient_username = parts[1]
            private_message = parts[2]

            recipient = self.server.get_client_by_username(recipient_username)

            if recipient:
                recipient.client_socket.send(f"[Приватное от {self.username}]: {private_message}\n".encode(ENCODING))
                self.client_socket.send(f"Вы отправили приватное сообщение {recipient_username}: {private_message}\n".encode(ENCODING))
                logger.info(f"[Приватное от {self.username} к {recipient_username}]: {private_message}") #Логирование приватного сообщения
            else:
                self.client_socket.send(f"Пользователь {recipient_username} не найден.\n".encode(ENCODING))

        except (ConnectionResetError, OSError) as e:
            logger.warning(f"Ошибка при отправке приватного сообщения {e}")


    def close_connection(self):
        """
        Закрывает соединение с клиентом и выполняет очистку.
        """
        if self.username:
            self.server.broadcast(f"{self.username} покинул чат.", exclude=self) # отправляем сообщение о выходе другим пользователям
            logger.info(f"{self.username} отключился.")
            self.server.remove_client(self)
        else:
            logger.info(f"Неизвестный клиент отключился.")
        self.is_running = False  # Останавливаем цикл обработки
        try:
             self.client_socket.close()
        except OSError as e:
            logger.error(f"Ошибка при закрытии сокета {self.client_address}: {e}")


class ChatServer:
    """
    Сервер для консольного чата.
    """

    def __init__(self, host, port):
        """
        Инициализация сервера.

        Args:
            host (str): Хост, на котором слушать.
            port (int): Порт, на котором слушать.
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []  # Список активных клиентов
        self.usernames = set() # Множество для хранения используемых имен пользователей

    def start(self):
        """
        Запускает сервер и начинает прослушивать входящие соединения.
        """
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CLIENTS)  # Максимум MAX_CLIENTS ожидающих подключений

            logger.info(f"Сервер запущен на {self.host}:{self.port}")

            while True:
                try:
                   client_socket, client_address = self.server_socket.accept()
                   client_socket.settimeout(60) # Таймаут для сокета клиента
                   logger.info(f"Принято подключение от {client_address}")
                   client_handler = ClientHandler(client_socket, client_address, self)
                   client_handler.daemon = True  # Поток-демон
                   client_handler.start()
                except socket.timeout:
                    logger.warning("Превышено время ожидания подключения.")
                except OSError as e:
                    logger.error(f"Ошибка при принятии соединения: {e}")
                    break

        except OSError as e:
            logger.error(f"Ошибка при запуске сервера: {e}")
        finally:
            self.stop()

    def stop(self):
         """
         Останавливает сервер, закрывая сокеты.
         """
         logger.info("Остановка сервера...")
         try:
             for client in self.clients:
                 client.close_connection()
             self.server_socket.close()
         except OSError as e:
             logger.error(f"Ошибка при закрытии сокетов: {e}")


    def broadcast(self, message, exclude=None):
        """
        Отправляет сообщение всем подключенным клиентам, кроме исключенного.

        Args:
            message (str): Сообщение для отправки.
            exclude (ClientHandler, optional): Клиент, который нужно исключить. Defaults to None.
        """
        encoded_message = message.encode(ENCODING)
        for client in self.clients:
            if client != exclude and client.is_running:  # Проверяем, что клиент активен
                try:
                   client.client_socket.send(encoded_message)
                except (ConnectionResetError, OSError) as e:
                    logger.warning(f"Ошибка при отправке сообщения {client.username}: {e}")
                    client.close_connection() # Закрываем соединение при ошибке

    def add_client(self, client_handler):
        """
        Добавляет нового клиента в список активных.

        Args:
            client_handler (ClientHandler): Обработчик клиента.
        """
        self.clients.append(client_handler)
        self.usernames.add(client_handler.username)

    def remove_client(self, client_handler):
        """
        Удаляет клиента из списка активных.

        Args:
            client_handler (ClientHandler): Обработчик клиента.
        """
        try:
            self.clients.remove(client_handler)
            self.usernames.remove(client_handler.username) # Удаляем имя пользователя из множества
        except ValueError:
            pass  # Если клиент уже был удален, ничего не делаем

    def is_username_taken(self, username):
        """
        Проверяет, используется ли имя пользователя.

        Args:
            username (str): Имя пользователя для проверки.

        Returns:
            bool: True, если имя пользователя занято, False - иначе.
        """
        return username in self.usernames

    def get_client_by_username(self, username):
        """
        Находит обработчик клиента по имени пользователя.

        Args:
            username (str): Имя пользователя.

        Returns:
            ClientHandler or None: Обработчик клиента, если найден, иначе None.
        """
        for client in self.clients:
            if client.username == username:
                return client
        return None



def run_client(host, port):
    """
    Функция для запуска клиента чата.
    """
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        client_socket.settimeout(60) # Таймаут для сокета клиента
        logger.info(f"Подключено к серверу {host}:{port}")

        def receive_messages():
            """
            Поток для получения сообщений от сервера.
            """
            while True:
                try:
                    message = client_socket.recv(1024).decode(ENCODING)
                    if not message:
                        break
                    print(message)
                except (ConnectionResetError, OSError) as e:
                    print(f"Ошибка при получении сообщения: {e}")
                    break
                except socket.timeout:
                    print("Превышено время ожидания от сервера.")
                    break


        receive_thread = threading.Thread(target=receive_messages, daemon=True)
        receive_thread.start()

        while True:
            try:
                message = input()
                if message.lower() == "/quit":
                    break
                client_socket.send(message.encode(ENCODING))
            except (ConnectionResetError, OSError) as e:
                print(f"Ошибка при отправке сообщения: {e}")
                break
            except socket.timeout:
                print("Превышено время ожидания от сервера.")
                break
    except ConnectionRefusedError:
        print("Не удалось подключиться к серверу. Убедитесь, что сервер запущен.")
    except OSError as e:
        print(f"Ошибка при работе с сокетом: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        logger.info("Клиент завершил работу.")

def main():
    """
    Основная функция для запуска сервера или клиента в зависимости от аргументов командной строки.
    """
    parser = argparse.ArgumentParser(description="Консольный чат на Python")
    parser.add_argument(
        "mode",
        choices=["server", "client"],
        help="Режим работы: server (запуск сервера) или client (запуск клиента)",
    )
    parser.add_argument(
        "--host", type=str, default=HOST, help="Адрес сервера (по умолчанию: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=PORT, help="Порт сервера (по умолчанию: 12345)"
    )

    args = parser.parse_args()

    if args.mode == "server":
        server = ChatServer(args.host, args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен.")
            server.stop()
    elif args.mode == "client":
        run_client(args.host, args.port)
    else:
        print("Неверный режим работы. Используйте 'server' или 'client'.")

if __name__ == "__main__":
    main()