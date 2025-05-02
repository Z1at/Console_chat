import socket
from ClientHandler import ClientHandler


class ChatServer:
    """
    Сервер для консольного чата.
    """

    def __init__(self, host, port, logger, max_clients, encoding):
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
        self.usernames = set()  # Множество для хранения используемых имен пользователей
        self.logger = logger
        self.MAX_CLIENTS = max_clients
        self.ENCODING = encoding

    def start(self):
        """
        Запускает сервер и начинает прослушивать входящие соединения.
        """

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.MAX_CLIENTS)  # Максимум MAX_CLIENTS ожидающих подключений

            self.logger.info(f"Сервер запущен на {self.host}:{self.port}")

            while True:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    # client_socket.settimeout(60)  # Таймаут для сокета клиента
                    self.logger.info(f"Принято подключение от {client_address}")
                    client_handler = ClientHandler(client_socket, client_address, self, self.logger, self.ENCODING)
                    client_handler.daemon = True  # Поток-демон
                    client_handler.start()
                # except socket.timeout:
                #     self.logger.warning("Превышено время ожидания подключения.")
                except OSError as e:
                    self.logger.error(f"Ошибка при принятии соединения: {e}")
                    break

        except OSError as e:
            self.logger.error(f"Ошибка при запуске сервера: {e}")
        finally:
            self.stop()

    def stop(self):
        """
        Останавливает сервер, закрывая сокеты.
        """

        self.logger.info("Остановка сервера...")
        try:
            for client in self.clients:
                client.close_connection()
            self.server_socket.close()
        except OSError as e:
            self.logger.error(f"Ошибка при закрытии сокетов: {e}")

    def broadcast(self, message, exclude=None):
        """
        Отправляет сообщение всем подключенным клиентам, кроме исключенного.

        Args:
            message (str): Сообщение для отправки.
            exclude (ClientHandler, optional): Клиент, который нужно исключить. Defaults to None.
        """

        encoded_message = message.encode(self.ENCODING)
        for client in self.clients:
            if client != exclude and client.is_running:  # Проверяем, что клиент активен
                try:
                    client.client_socket.send(encoded_message)
                except (ConnectionResetError, OSError) as e:
                    self.logger.warning(f"Ошибка при отправке сообщения {client.username}: {e}")
                    client.close_connection()  # Закрываем соединение при ошибке

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
            self.usernames.remove(client_handler.username)  # Удаляем имя пользователя из множества
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
