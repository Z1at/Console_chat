import socket
import threading
# from Main import self.ENCODING
# from Main import self.logger


class ClientHandler(threading.Thread):
    """
    Обработчик для каждого подключенного клиента.
    """

    def __init__(self, client_socket, client_address, server, logger, encoding):
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
        self.client_socket.settimeout(60)  # Установка таймаута сокета
        self.logger = logger
        self.ENCODING = encoding

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
                    message = self.client_socket.recv(1024).decode(self.ENCODING)
                    if not message:
                        break  # Клиент отключился

                    self.handle_message(message)

                except socket.timeout:
                    self.logger.warning(f"Превышено время ожидания от {self.username}. Закрытие соединения.")
                    break  # Прекращаем обработку клиента при таймауте сокета
                except (ConnectionResetError, OSError) as e:
                    self.logger.warning(f"Ошибка при получении сообщения от {self.username}: {e}")
                    break  # Прекращаем обработку клиента при ошибке сокета

        finally:
            self.close_connection()

    def get_username(self):
        """
        Получает имя пользователя от клиента.

        Returns:
            str: Имя пользователя, или None если не удалось получить имя.
        """
        try:
            self.client_socket.send("Введите имя пользователя: ".encode(self.ENCODING))
            self.client_socket.settimeout(10)  # Таймаут для получения имени пользователя
            username = self.client_socket.recv(1024).decode(self.ENCODING).strip()
            self.client_socket.settimeout(60)  # Сбрасываем таймаут для дальнейшей работы
            if not username:
                self.client_socket.send("Имя пользователя не может быть пустым.\n".encode(self.ENCODING))
                return None
            if self.server.is_username_taken(username):
                self.client_socket.send("Это имя пользователя уже занято.\n".encode(self.ENCODING))
                return None
            return username
        except socket.timeout:
            self.client_socket.send("Превышено время ввода имени пользователя.\n".encode(self.ENCODING))
            self.logger.warning(f"Не удалось получить имя пользователя от {self.client_address} (таймаут)")
            return None  #Возврат None при таймауте
        except (ConnectionResetError, OSError):
            self.logger.warning(f"Не удалось получить имя пользователя от {self.client_address}")
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
            self.logger.info(f"[{self.username}]: {message}")  #логирование

    def send_private_message(self, message):
        """
        Отправляет личное сообщение другому клиенту.

        Args:
            message (str): Текст сообщения, начинающийся с "/to".
        """
        try:
            parts = message.split(" ", 2)
            if len(parts) < 3:
                self.client_socket.send(
                    "Неверный формат личного сообщения. Используйте /to <имя_получателя> <сообщение>\n".encode(
                        self.ENCODING))
                return

            recipient_username = parts[1]
            private_message = parts[2]

            recipient = self.server.get_client_by_username(recipient_username)

            if recipient:
                recipient.client_socket.send(f"[Приватное от {self.username}]: {private_message}\n".encode(self.ENCODING))
                self.client_socket.send(
                    f"Вы отправили приватное сообщение {recipient_username}: {private_message}\n".encode(self.ENCODING))
                self.logger.info(
                    f"[Приватное от {self.username} к {recipient_username}]: {private_message}")  #Логирование приватного сообщения
            else:
                self.client_socket.send(f"Пользователь {recipient_username} не найден.\n".encode(self.ENCODING))

        except (ConnectionResetError, OSError) as e:
            self.logger.warning(f"Ошибка при отправке приватного сообщения {e}")

    def close_connection(self):
        """
        Закрывает соединение с клиентом и выполняет очистку.
        """
        if self.username:
            self.server.broadcast(f"{self.username} покинул чат.",
                                  exclude=self)  # отправляем сообщение о выходе другим пользователям
            self.logger.info(f"{self.username} отключился.")
            self.server.remove_client(self)
        else:
            self.logger.info(f"Неизвестный клиент отключился.")
        self.is_running = False  # Останавливаем цикл обработки
        try:
            self.client_socket.close()
        except OSError as e:
            self.logger.error(f"Ошибка при закрытии сокета {self.client_address}: {e}")


def run_client(host, port, logger, ENCODING):
    """
    Функция для запуска клиента чата.
    """
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        client_socket.settimeout(60)  # Таймаут для сокета клиента
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
