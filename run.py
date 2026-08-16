"""
Точка входа в приложение.
Запускает main функцию из app.main.
"""
import asyncio
from app.main import main

if __name__ == "__main__":
    asyncio.run(main())