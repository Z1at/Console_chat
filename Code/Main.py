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
    - ЯП: Python 3.13.3
    - Код: Документирован
    - Зависимости: Стандартная библиотека Python
    - Установка: Не предусмотрена установка через RPM, так как это не типичная установка для Python скриптов.  Пример установки см. в разделе "Инструкция по установке".

Требования к документации:
    - Исходный код
    - Используемые модули/библиотеки
    - Инструкция по установке
    - Примеры использования
"""


import logging
import argparse
import sys
from ChatServer import ChatServer
from ClientHandler import run_client


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
        server = ChatServer(args.host, args.port, logger, MAX_CLIENTS, ENCODING)
        try:
            server.start()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен.")
            server.stop()
    elif args.mode == "client":
        run_client(args.host, args.port, logger, ENCODING)
    else:
        print("Неверный режим работы. Используйте 'server' или 'client'.")


if __name__ == "__main__":
    main()
