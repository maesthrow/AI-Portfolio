from __future__ import annotations

from datetime import date
from typing import Iterable
import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.settings import settings

from app.models.profile import Profile
from app.models.contact import Contact
from app.models.experience import CompanyExperience
from app.models.experience_project import ExperienceProject
from app.models.project import Project, ProjectTechnology
from app.models.publication import Publication
from app.models.stats import Stat
from app.models.tech_focus import TechFocus, TechFocusTag
from app.models.technology import Technology
from app.models.hero_tag import HeroTag
from app.models.focus_area import FocusArea, FocusAreaBullet
from app.models.work_approach import WorkApproach, WorkApproachBullet
from app.models.section_meta import SectionMeta

# автономная сессия, как в старых сидерах
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# ---------- утилиты ----------

def get_one(session, model, **filters):
    return session.execute(select(model).filter_by(**filters)).scalar_one_or_none()


def upsert_one(session, model, identity: dict, payload: dict):
    # Identity fields are used to locate the record; don't duplicate/overwrite them in payload.
    payload = {k: v for k, v in payload.items() if k not in identity}
    obj = get_one(session, model, **identity)
    if obj is None:
        obj = model(**identity, **payload)
        session.add(obj)
    else:
        changed = False
        for field, val in payload.items():
            if getattr(obj, field) != val:
                setattr(obj, field, val)
                changed = True
        if changed:
            session.flush()
    return obj


# ---------- данные ----------

PROFILE_DATA = {
    "id": 1,
    "full_name": "Дмитрий Каргин",
    "title": "AI-инженер • Python-разработчик",
    "subtitle": "AI-agents • LLM • RAG • CV • Python • Backend",
    "location": "Самара, Россия",
    "status": "ready_to_connect_",
    "avatar_url": "https://avatars.githubusercontent.com/u/113206960?s=400&u=3168146b785d59a77ded3353c07c1de8697abcaa&v=4",
    "summary_md": (
        "AI-инженер с продуктовым подходом и опытом backend-разработки более пяти лет.\n"
        "Внедрял AI-решения в коммерческих проектах; фокус — архитектура агентных систем, качество продукта и бизнес-эффект."
    ),
    "hero_headline": "AI Agent Engineer • Python Developer",
    "hero_description": "Строю надежные AI-системы — от идеи до запуска.",
    "current_position": "Senior AI Agent Developer в Сбере",
}

CONTACTS_DATA = [
    {
        "kind": "telegram",
        "label": "Telegram",
        "value": "@kargindmitriy",
        "url": "https://t.me/kargindmitriy",
        "order_index": 10,
        "is_primary": True,
    },
    {
        "kind": "email",
        "label": "Email",
        "value": "dmitriy3kargin@gmail.com",
        "url": "",
        "order_index": 20,
        "is_primary": False,
    },
    {
        "kind": "hh",
        "label": "hh.ru",
        "value": "Dmitriy Kargin",
        "url": "https://samara.hh.ru/resume/4ff077d4ff0f9bb97a0039ed1f767833386370",
        "order_index": 30,
        "is_primary": False,
    },
    {
        "kind": "linkedin",
        "label": "LinkedIn",
        "value": "Dmitriy Kargin",
        "url": "https://www.linkedin.com/in/dmitriy-kargin-ba08b932b",
        "order_index": 40,
        "is_primary": False,
    },
    {
        "kind": "github",
        "label": "GitHub",
        "value": "maesthrow",
        "url": "https://github.com/maesthrow",
        "order_index": 50,
        "is_primary": False,
    },
    {
        "kind": "leetcode",
        "label": "LeetCode",
        "value": "maesthrow",
        "url": "https://leetcode.com/maesthrow/",
        "order_index": 60,
        "is_primary": False,
    },
]

EXPERIENCE_DATA = [
    # Aston / t2 — Нейросети
    {
        "role": "Python / ML Engineer",
        "company_name": "Aston",
        "company_slug": "aston",
        "company_url": "https://astondevs.ru",
        "project_name": "t2 — Нейросети",
        "project_slug": "t2-ml",
        "project_url": None,
        "start_date": date(2024, 10, 28),
        "end_date": date(2025, 12, 30),
        "is_current": False,
        "kind": "commercial",
        "company_role_md": "Строил LLM/RAG-системы и CV-сервисы, проектировал backend-архитектуру, пайплайны обучения моделей и интеграции с внутренними сервисами t2.",
        "summary_md": (
            "Проект по разработке сервисов на базе ML-решений."
        ),
        "achievements_md": (
            "- Внедрил сервис компьютерного зрения для ребрендинга t2/Tele2: "
            "обучение моделей, обработка отчетов по торговым точкам.\n"
            "- Создал умного помощника с LLM + RAG для расчёта штрафов по договорам.\n"
            "- Разработал MVP бэкенда авто-обучения и инференса CV-моделей.\n"
        ),
        "description_md": None,
        "order_index": 10,
    },
    # АЛОР
    {
        "role": "Python Backend Developer",
        "company_name": "ООО «АЛОР +»",
        "company_slug": "alor",
        "company_url": "https://www.alorbroker.ru",
        "project_name": "АЛОР БРОКЕР",
        "project_slug": "alor-broker",
        "project_url": None,
        "start_date": date(2024, 5, 13),
        "end_date": date(2024, 10, 25),
        "is_current": False,
        "kind": "commercial",
        "company_role_md": "Разрабатывал и поддерживал backend‑сервисы: оптимизация, рефакторинг, интеграции с внутренними и внешними системами.",
        "summary_md": (
            "Биржевый брокер для лиц, осуществляющих финансовые операции с ценными бумагами."
        ),
        "achievements_md": (
            "- Запустил сервис нотификаций для бэк-офиса и клиентов.\n"
            "- Переписал код трех сервисов под новый стек.\n"
            "- Интегрировал сервис отправки отчётов в ФНС с API Контур.Экстерн.\n"
        ),
        "description_md": None,
        "order_index": 20,
    },
    # Spargo / F3 TAIL
    {
        "role": ".NET/Python Backend Developer",
        "company_name": "АО «Спарго Технологии»",
        "company_slug": "spargo",
        "company_url": "https://www.spargo.ru",
        "project_name": "F3 TAIL",
        "project_slug": "f3-tail",
        "project_url": None,
        "start_date": date(2023, 8, 4),
        "end_date": date(2024, 5, 10),
        "is_current": False,
        "kind": "commercial",
        "company_role_md": "Развивал backend сервисов автоматизации аптек: фикс багов, интеграции, оптимизация нагруженных систем и баз данных.",
        "summary_md": (
            "Сервисы автоматизации аптек и розничной торговли."
        ),
        "achievements_md": (
            "- Оптимизировал обмен с Единым Справочником (ускорение > x3).\n"
            "- Внедрил сервис мониторинга и логирования сбоев.\n"
            "- Разработал Telegram-бота службы поддержки.\n"
        ),
        "description_md": None,
        "order_index": 30,
    },
    # РКЦ «Прогресс» / СКИО
    {
        "role": "Backend Developer",
        "company_name": "АО «РКЦ «Прогресс»",
        "company_slug": "progress",
        "company_url": "https://samspace.ru",
        "project_name": "СКИО",
        "project_slug": "skio",
        "project_url": None,
        "start_date": date(2021, 9, 1),
        "end_date": date(2023, 8, 1),
        "is_current": False,
        "kind": "commercial",
        "company_role_md": "Разрабатывал программное обеспечение для подразделений испытательного центра ракетно-космического предприятия.",
        "summary_md": (
            "Система контроля испытательного оборудования."
        ),
        "achievements_md": (
            "- По личной инициативе предложил идею и самостоятельно разработал систему контроля испытательного оборудования (СКИО).\n"
            "- Успешно запустил и внедрил систему в работу подразделений испытательного центра.\n"
            "- Оптимизировал производственный процесс предприятия в рамках бережливого производства.\n"
        ),
        "description_md": None,
        "order_index": 40,
    },
]

PROJECTS_DATA = [
    {
        "name": "t2 — Нейросети",
        "slug": "t2-ml",
        "description_md": (
            "Развитие ML-платформы компании t2: CV-сервисы для автоматизации процессов ребрендинга, "
            "LLM + RAG-системы, backend авто-обучения и инференса CV-моделей + MLOps."
        ),
        "long_description_md": (
            "- Сервис на базе компьютерного зрения для распознавания бренда на тысячах фотографий с точек продаж.\n"
            "- AI-ассистент с RAG для расчёта штрафов и по договорам (LangChain/LangGraph, LoRA, vLLM, Qdrant).\n"
            "- MLOps: MLflow, Celery, RabbitMQ, пайплайн авто-обучения, валидации и инференса ML-моделей компьютерного зрения.\n"
            "- Backend на FastAPI, интеграции с внутренними сервисами t2."
        ),
        "period": "2024 — 2025",
        "company_name": "t2 (проект в Aston)",
        "company_website": "https://t2.ru",
        "domain": "Telecom • ML",
        "featured": False,
        "repo_url": None,
        "demo_url": None,
        "technologies": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "SQLAlchemy",
            "Alembic",
            "Redis",
            "Celery",
            "RabbitMQ",
            "Ultralytics",
            "YOLO",
            "Detectron2",
            "Computer Vision",
            "vLLM",
            "LiteLLM",
            "LangChain",
            "LangGraph",
            "RAG",
            "ChromaDB",
            "Qdrant",
            "MLflow",
            "Docker",
        ],
    },
    {
        "name": "АЛОР БРОКЕР",
        "slug": "alor-broker",
        "description_md": (
            "Серверная разработка микросервисов для биржевого брокера, интеграции с внешними системами и API."
        ),
        "long_description_md": None,
        "period": "2024",
        "company_name": "ООО «АЛОР +»",
        "company_website": "https://www.alorbroker.ru",
        "domain": "FinTech",
        "featured": False,
        "repo_url": None,
        "demo_url": None,
        "technologies": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Pydantic",
            "SQLAlchemy",
            "Alembic",
            "RabbitMQ",
            "Celery",
            "Docker",
        ],
    },
    {
        "name": "F3 TAIL",
        "slug": "f3-tail",
        "description_md": (
            "Сервисы для автоматизации аптек и розничной торговли: оптимизация, интеграция, мониторинг, "
            "создание бота службы поддержки."
        ),
        "long_description_md": None,
        "period": "2023–2024",
        "company_name": "АО «Спарго Технологии»",
        "company_website": "https://www.spargo.ru",
        "domain": "Retail",
        "featured": False,
        "repo_url": None,
        "demo_url": None,
        "technologies": [
            "C#"
            ".NET Framework",
            ".NET Core",
            "ASP.NET Core",
            "MS SQL Server",
            "Python",
            "PostgreSQL",
            "APScheduler",
            "aiogram",
            "aiogram-dialog",
            "Docker",
        ],
    },
    {
        "name": "СКИО",
        "slug": "skio",
        "description_md": (
            "Создание системы контроля испытательного оборудования (СКИО): "
            "полный цикл разработки от проектирования базы данных и архитектуры приложения до реализации backend, ui, тестирования и запуска."
        ),
        "period": "2021–2023",
        "company_name": "АО «РКЦ «Прогресс»",
        "company_website": "https://samspace.ru",
        "domain": "Industrial • Rocket Science",
        "featured": False,
        "repo_url": None,
        "demo_url": None,
        "technologies": [
            "C#",
            ".NET Framework",
            "MS SQL Server",
            "ADO.NET",
        ],
    },
    {
        "name": "HyperKeeper",
        "slug": "hyperkeeper",
        "description_md": (
            "Telegram-бот — персональное хранилище файлов и заметок с иерархией папок, "
            "шарингом между пользователями и RAG-поиском по контенту. "
            "Встроенный LLM-чат (GigaChat) с сохранением истории диалогов."
        ),
        "long_description_md": (
            "- Иерархическая структура папок с неограниченной вложенностью, постраничные заметки с файлами и медиа, пинкод на папки.\n"
            "- Шаринг записей и папок между пользователями, поиск по всему хранилищу или по отдельным папкам/записям/файлам.\n"
            "- LLM-модуль на GigaChat с RAG-поиском по заметкам (LangChain, ChromaDB), сохранение и переключение между диалогами.\n"
            "- UI через aiogram-dialog: постраничная навигация, настройки, выбор языка, модуль связи с поддержкой."
        ),
        "period": "2023 — 2024",
        "company_name": None,
        "company_website": "https://github.com/maesthrow",
        "domain": "Telegram Bot",
        "featured": True,
        "repo_url": "https://github.com/maesthrow/HyperKeeperBot",
        "demo_url": "https://t.me/HyperKeeperBot",
        "technologies": [
            "Python",
            "aiogram",
            "aiogram-dialog",
            "MongoDB",
            "LLM",
            "LangChain",
            "GigaChain",
            "RAG",
            "ChromaDB",
            "Redis",
            "Docker",
        ],
    },
    {
        "name": "AI-Portfolio",
        "slug": "ai-portfolio",
        "description_md": (
            "Сайт-портфолио в стиле киберпанк с встроенным AI-агентом. "
            "Агент отвечает на вопросы по содержимому портфолио, отправляет CV на email "
            "и поддерживает многоходовый диалог со стримингом ответов в реальном времени."
        ),
        "long_description_md": (
            "- Микросервисная архитектура: Content API и RAG API на FastAPI, фронтенд на Next.js (SSR), оркестрация через Docker Compose.\n"
            "- AI-агент на LangGraph с гибридным роутером (regex fast-path + LLM-классификация) и 6 независимыми LLM-ролями (GigaChat, DeepSeek, Qwen).\n"
            "- RAG-пайплайн: векторное хранилище pgvector, граф знаний, гибридный поиск (dense + BM25), кросс-энкодер реранкер, кэш эмбеддингов и планов в Redis.\n"
            "- Стриминг NDJSON с отображением этапов пайплайна в реальном времени (планирование → поиск → верификация → ответ).\n"
            "- Отправка CV через многоходовый диалог с агентом, rate-limiting по IP и email."
        ),
        "period": "2025 — н.в.",
        "company_name": None,
        "company_website": "https://github.com/maesthrow",
        "domain": "Web AI",
        "featured": True,
        "repo_url": "https://github.com/maesthrow/AI-Portfolio",
        "demo_url": "https://ai-folio.ru",
        "technologies": [
            "Python",
            "FastAPI",
            "LLM",
            "LangChain",
            "LangGraph",
            "RAG",
            "pgvector",
            "PostgreSQL",
            "Redis",
            "LiteLLM",
            "vLLM",
            "Docker",
            "Next.js",
            "TypeScript",
            "Tailwind CSS",
        ],
    },
    {
        "name": "ReAct-Agent",
        "slug": "react-agent",
        "description_md": (
            "Прототип AI-агента на Python, демонстрирующий эволюцию от простого чата с LLM "
            "до агента с инструментами и персистентной памятью. "
            "Подходит для обучения и экспериментов с агентным стеком."
        ),
        "long_description_md": (
            "- Три этапа: базовый чат → ReAct-агент с tool-calling → агент с персистентной памятью (LangGraph MemorySaver).\n"
            "- Кастомные инструменты: поиск в DuckDuckGo (ru-RU) и логирование результатов в файл.\n"
            "- LLM-провайдер GigaChat через LangChain, чекпойнтинг диалогов по thread_id."
        ),
        "period": "2025",
        "company_name": None,
        "company_website": "https://github.com/maesthrow",
        "domain": "Prototype",
        "featured": True,
        "repo_url": "https://github.com/maesthrow/ReAct-Agent",
        "demo_url": None,
        "technologies": [
            "LLM",
            "ReAct",
            "LangChain",
            "LangGraph",
            "DuckDuckGo",
        ],
    },
]

PUBLICATIONS_DATA = [
    # {
    #     "title": "Гайд: AI-агент на GigaChat и LangGraph (от архитектуры до валидации)",
    #     "year": 2025,
    #     "source": "Habr",
    #     "url": "https://habr.com/ru/articles/xxxxx/",
    #     "badge": None,
    #     "description_md": (
    #         "Пошаговый разбор архитектуры AI-агента на базе GigaChat и LangGraph "
    #         "на примере Lean Canvas."
    #     ),
    #     "order_index": 10,
    # },
    # {
    #     "title": "Какой плащ был у Понтия Пилата? Отвечает GigaChat",
    #     "year": 2024,
    #     "source": "Habr",
    #     "url": "https://habr.com/ru/articles/yyyyy/",
    #     "badge": None,
    #     "description_md": "Развлекательный кейс с использованием GigaChat и RAG-подхода.",
    #     "order_index": 20,
    # },
]

STATS_DATA = [
    {
        "key": "repos",
        "label": "GitHub репозитории",
        "value": "30+",
        "hint": "Open-source • pet-проекты",
        "group_name": "about",
        "order_index": 10,
    },
    {
        "key": "experience_years",
        "label": "Опыт в разработке",
        "value": "5+ лет",
        "hint": "Python/.NET • Backend • ML",
        "group_name": "about",
        "order_index": 20,
    },
    {
        "key": "ai_projects",
        "label": "AI-проекты",
        "value": "8+",
        "hint": "AI-агенты • LLM • RAG • CV",
        "group_name": "about",
        "order_index": 30,
    },
]

TECH_FOCUS_DATA = [
    {
        "label": "LLM, RAG и AI-агенты",
        "description": "AI-агенты, LLM, RAG-системы, работа с векторными хранилищами.",
        "order_index": 10,
        "tags": [
            "LangChain",
            "LangGraph",
            "RAG",
            "ReAct",
            "pgvector",
            "ChromaDB",
            "Qdrant",
            "OpenAI API",
            "GigaChat",
            "Qwen",
            "DeepSeek",
        ],
    },
    {
        "label": "ML и CV",
        "description": "Машинное обучение, компьютерное зрение.",
        "order_index": 20,
        "tags": [
            "PyTorch",
            "Ultralytics",
            "YOLO",
            "Detectron2",
            "OpenCV",
            "NumPy",
            "Pandas",
        ],
    },
    {
        "label": "Backend и интеграции",
        "description": "Python backend, API, брокеры сообщений, фоновые задачи.",
        "order_index": 30,
        "tags": [
            "Python",
            "FastAPI",
            "SQLAlchemy",
            "PostgreSQL",
            "Redis",
            "Celery",
            "RabbitMQ",
        ],
    },
    {
        "label": "MLOps и инфраструктура",
        "description": "Инференс, мониторинг, развертывание моделей.",
        "order_index": 40,
        "tags": [
            "Docker",
            "MLflow",
            "vLLM",
            "LiteLLM",
            "TEI",
            "GitLab",
        ],
    },
]

HERO_TAGS_DATA = [
    {"name": "AI-agents", "order_index": 10},
    {"name": "LLM", "order_index": 20},
    {"name": "RAG", "order_index": 30},
    {"name": "CV", "order_index": 40},
    {"name": "MLOps", "order_index": 50},
    {"name": "Python", "order_index": 60},
    {"name": "Backend", "order_index": 70},
    {"name": "GitHub", "url": "https://github.com/maesthrow", "icon": "github", "order_index": 80},
    {"name": "Telegram", "url": "https://t.me/kargindmitriy", "icon": "telegram", "order_index": 90},
    {"name": "LinkedIn", "url": "https://www.linkedin.com/in/dmitriy-kargin", "icon": "linkedin", "order_index": 100},
]

FOCUS_AREAS_DATA = [
    {
        "title": "LLM / AI-Agents / RAG",
        "is_primary": True,
        "order_index": 10,
        "bullets": [
            "Fine-tuning и LoRA-адаптеры, промпт-инжиниринг под прод",
            "Агентные сценарии и tool-calling (ReAct, Plan-and-Execute, LangGraph)",
            "RAG-архитектуры: база знаний, retrieval + rerank, контекстная сборка",
            "Оценка качества: golden set, регрессионные тесты, groundedness, success rate",
        ],
    },
    {
        "title": "CV",
        "is_primary": False,
        "order_index": 20,
        "bullets": [
            "Классификация, детекция и сегментация объектов",
            "Пайплайны обработки изображений: датасеты, аугментации, препроцессинг",
            "Цикл улучшения моделей: валидация → сложные кейсы → дообучение",
            "Запуск CV-сервисов в продакшене и контроль качества",
        ],
    },
    {
        "title": "Backend / MLOps",
        "is_primary": False,
        "order_index": 30,
        "bullets": [
            "Backend для AI: API, микросервисы, базы данных и кэш",
            "Асинхронные задачи и очереди: Celery, RabbitMQ",
            "MLOps: пайплайны обучения/дообучения, инференс, контейнеризация",
            "Интеграции с внешними API и внутренними сервисами",
        ],
    },
]

WORK_APPROACHES_DATA = [
    {
        "title": "Продуктовый подход",
        "icon": "lightbulb",
        "order_index": 10,
        "bullets": [
            "Начинаю с бизнес-задачи и метрик успеха, а не с выбора технологии",
            "Учитываю edge-кейсы, неоднозначности и типовые ошибки заранее",
            "Выстраиваю цикл улучшений: логи → метрики → правки AI-компонентов → дообучение и регрессии",
        ],
    },
    {
        "title": "Архитектура и интеграции",
        "icon": "blocks",
        "order_index": 20,
        "bullets": [
            "Строю архитектуру AI-сервисов вокруг LLM: агенты, RAG, инструменты и API",
            "Разделяю контекст, действия и бизнес-логику — чтобы масштабировать компоненты независимо",
            "Делаю интеграции надежными: контракты данных, обработка ошибок и устойчивость",
        ],
    },
    {
        "title": "Запуск и поддержка",
        "icon": "rocket",
        "order_index": 30,
        "bullets": [
            "Вывожу модели и AI-сервисы в прод: автоматизация, релизы, rollback и стабильная эксплуатация",
            "Настраиваю мониторинг и алертинг: качество, ошибки, задержки, стоимость",
            "Документирую систему: архитектура, runbook, сценарии отказов и восстановление",
        ],
    },
]

SECTION_META_DATA = [
    {
        "section_key": "experience",
        "title": "Коммерческий опыт",
        "subtitle": "Коммерческие проекты и компании: AI-системы, backend-сервисы и интеграционные решения",
    },
    {
        "section_key": "contacts",
        "title": "Связаться со мной",
        "subtitle": "Свяжитесь со мной напрямую или через AI-агента на сайте",
    },
    {
        "section_key": "projects",
        "title": "Избранные проекты",
        "subtitle": "Проекты, которые я создал и продолжаю развивать",
    },
    {
        "section_key": "tech_focus",
        "title": "Технологический фокус",
        "subtitle": "Основные направления и технологии, с которыми я работаю",
    },
    {
        "section_key": "how_i_work",
        "title": "Как я работаю с AI",
        "subtitle": "Мой подход к разработке AI-продуктов",
    },
    {
        "section_key": "publications",
        "title": "Контент и публикации",
        "subtitle": "Статьи и материалы по AI/ML и разработке",
    },
]

# Технологии с категориями для фильтрации (TZ v3)
# Категории: language, database, vector_store, framework, ml_framework, concept, library, tool, message_broker
TECHNOLOGIES_WITH_CATEGORIES = {
    # Programming Languages
    "Python": "language",
    "TypeScript": "language",
    "C#": "language",

    # Databases
    "PostgreSQL": "database",
    "Redis": "database",
    "MongoDB": "database",
    "MS SQL Server": "database",

    # Vector Stores
    "ChromaDB": "vector_store",
    "Qdrant": "vector_store",
    "pgvector": "vector_store",

    # CSS Frameworks
    "Tailwind CSS": "framework",

    # Frameworks
    "FastAPI": "framework",
    "ASP.NET Core": "framework",
    ".NET Core": "framework",
    ".NET Framework" : "framework",
    "Next.js": "framework",

    # ML/AI Frameworks
    "LangChain": "ml_framework",
    "LangGraph": "ml_framework",
    "GigaChain": "ml_framework",
    "vLLM": "ml_framework",
    "PyTorch": "ml_framework",
    "Ultralytics": "ml_framework",
    "YOLO": "ml_framework",
    "Detectron2": "ml_framework",

    # MLOps
    "LiteLLM": "mlops",
    "MLflow": "mlops",

    # Concept
    "RAG": "concept",
    "LLM": "concept",
    "ReAct": "concept",
    "Computer Vision": "concept",

    # Libraries
    "Pydantic": "library",
    "SQLAlchemy": "library",
    "Alembic": "library",
    "psycopg": "library",
    "APScheduler": "library",
    "aiogram": "library",
    "aiogram-dialog": "library",
    "Celery": "library",
    "pytest": "library",
    "ADO.NET": "library",
    "DuckDuckGo": "library",

    # Tools
    "Docker": "tool",
    "Git": "tool",
    "GitLab": "tool",
    "Azure DevOps": "tool",

    # Message Brokers
    "RabbitMQ": "message_broker",
    "Kafka": "message_broker",
}

# Sorted list for backward compatibility
TECHNOLOGIES_DATA = sorted(TECHNOLOGIES_WITH_CATEGORIES.keys())

RAG_DOCUMENTS_DATA = [
    # переносим из старых сидеров «documents» в более общий RagDocument
    # {
    #     "type": "project_doc",
    #     "title": "Архитектура сервиса LLM + RAG (t2)",
    #     "body": "Схема архитектуры сервиса LLM + RAG для проектов t2.",
    #     "url": "https://example.org/aston-llm-rag-arch.pdf",
    #     "tags": ["t2", "RAG", "architecture"],
    #     "metadata": {"project_slug": "t2-ml"},
    # },
    # {
    #     "type": "project_doc",
    #     "title": "Схема CV-пайплайна t2",
    #     "body": "Диаграмма пайплайна CV-обработки для ребрендинга t2/Tele2.",
    #     "url": "https://example.org/aston-cv-pipeline-diagram.pdf",
    #     "tags": ["t2", "cv", "pipeline"],
    #     "metadata": {"project_slug": "t2-ml"},
    # },
    # {
    #     "type": "project_doc",
    #     "title": "Архитектура HyperKeeper",
    #     "body": "Схема архитектуры Telegram-бота HyperKeeper.",
    #     "url": "https://example.org/hyperkeeper-arch.pdf",
    #     "tags": ["hyperkeeper", "architecture"],
    #     "metadata": {"project_slug": "hyperkeeper"},
    # },
]


# ---------- функции-сидеры ----------

def seed_profile(session):
    identity = {"id": PROFILE_DATA["id"]}
    payload = {k: v for k, v in PROFILE_DATA.items() if k != "id"}
    upsert_one(session, Profile, identity, payload)


def seed_contacts(session):
    # ensure unique contact per kind; drop any duplicates before upserting
    existing = session.execute(select(Contact).order_by(Contact.id.asc())).scalars().all()
    seen_kinds: dict[str, Contact] = {}
    for contact in existing:
        if contact.kind in seen_kinds:
            session.delete(contact)
        else:
            seen_kinds[contact.kind] = contact
    if len(seen_kinds) != len(existing):
        session.flush()

    for idx, data in enumerate(CONTACTS_DATA, start=1):
        identity = {"kind": data["kind"]}
        payload = {**data, "order_index": data.get("order_index", idx * 10)}
        upsert_one(session, Contact, identity, payload)


def seed_experience(session):
    used_slugs = set()
    for idx, data in enumerate(EXPERIENCE_DATA, start=1):
        identity = {"id": idx}
        payload = {**data, "order_index": data.get("order_index", idx * 10)}

        base_slug = data.get("company_slug") or data.get("company_name") or data.get("project_name") or "company"
        slug = re.sub(r"[^a-z0-9]+", "-", base_slug.lower()).strip("-") or f"company-{idx}"
        original_slug = slug
        counter = 1
        while slug in used_slugs:
            slug = f"{original_slug}-{counter}"
            counter += 1
        used_slugs.add(slug)
        payload["company_slug"] = slug
        payload["company_summary_md"] = data.get("summary_md")
        payload["company_role_md"] = (
            data.get("company_role_md")
            or data.get("summary_md")
            or data.get("description_md")
        )

        company: CompanyExperience = upsert_one(session, CompanyExperience, identity, payload)

        # Create/update single project per company experience for now
        proj_name = data.get("project_name") or (data.get("company_name") or f"Project {idx}")
        proj_slug = data.get("project_slug") or slug
        if data.get("start_date"):
            start_year = data["start_date"].year
            if data.get("is_current") or data.get("end_date") is None:
                period = f"{start_year} — н.в."
            elif data.get("end_date"):
                period = f"{start_year} — {data['end_date'].year}"
            else:
                period = None
        else:
            period = None

        proj_payload = {
            "experience_id": company.id,
            "name": proj_name,
            "slug": proj_slug,
            "period": period,
            "description_md": data.get("summary_md") or proj_name,
            "achievements_md": data.get("achievements_md") or "",
            "order_index": data.get("order_index", idx * 10),
        }
        project_identity = {"experience_id": company.id, "slug": proj_payload["slug"]}
        upsert_one(session, ExperienceProject, project_identity, proj_payload)


def seed_projects(session):
    for idx, data in enumerate(PROJECTS_DATA, start=1):
        identity = {"id": idx}
        tech_names = data.get("technologies", [])
        payload = data.copy()
        payload.pop("technologies", None)
        proj = upsert_one(session, Project, identity, payload)

        # связь many-to-many «project ↔ technologies» в новой схеме уже реализована
        # предположим, есть вспомогательный метод или отдельная таблица project_technology.
        # Здесь только гарантируем наличие Technology; связку настроишь в API или
        # отдельным скриптом, если нужно.


def seed_publications(session):
    for idx, data in enumerate(PUBLICATIONS_DATA, start=1):
        identity = {"id": idx}
        payload = {**data, "order_index": data.get("order_index", idx * 10)}
        upsert_one(session, Publication, identity, payload)


def seed_stats(session):
    for idx, data in enumerate(STATS_DATA, start=1):
        identity = {"id": idx}
        payload = {**data, "order_index": data.get("order_index", idx * 10)}
        upsert_one(session, Stat, identity, payload)


def seed_tech_focus(session):
    for idx, block in enumerate(TECH_FOCUS_DATA, start=1):
        tags = block.get("tags", [])
        identity = {"id": idx}
        payload = {
            "label": block["label"],
            "description": block.get("description"),
            "order_index": block.get("order_index", idx * 10),
        }
        focus: TechFocus = upsert_one(session, TechFocus, identity, payload)

        # теги привяжем по имени + tech_focus_id
        for t_idx, name in enumerate(tags, start=1):
            identity_tag = {
                "name": name,
                "order_index": t_idx * 10,
                "tech_focus_id": focus.id,
            }
            # здесь удобнее использовать get_one напрямую
            tag = session.execute(
                select(TechFocusTag).filter_by(
                    tech_focus_id=focus.id,
                    name=name,
                )
            ).scalar_one_or_none()
            if tag is None:
                tag = TechFocusTag(
                    tech_focus_id=focus.id,
                    name=name,
                    order_index=t_idx * 10,
                )
                session.add(tag)


def seed_technologies(session):
    for idx, name in enumerate(TECHNOLOGIES_DATA, start=1):
        slug = (
            name.lower()
            .replace(" ", "-")
            .replace("(", "")
            .replace(")", "")
            .replace("/", "-")
        )
        identity = {"slug": slug}
        # Get category from mapping (TZ v3 requirement)
        category = TECHNOLOGIES_WITH_CATEGORIES.get(name)
        payload = {"name": name, "category": category, "order_index": idx * 10}
        upsert_one(session, Technology, identity, payload)
    # Needed because SessionLocal is configured with autoflush=False; later queries must see these rows.
    session.flush()


def seed_projects_with_tech(session):
    def slugify_tech(name: str) -> str:
        return (
            name.lower()
            .replace(" ", "-")
            .replace("(", "")
            .replace(")", "")
            .replace("/", "-")
        )

    for idx, data in enumerate(PROJECTS_DATA, start=1):
        tech_names = data.get("technologies", [])
        payload = data.copy()
        payload.pop("technologies", None)
        slug = payload.get("slug")
        identity = {"slug": slug}
        proj = upsert_one(session, Project, identity, payload)
        if proj.id is None:
            session.flush()

        for t_idx, tech_name in enumerate(tech_names, start=1):
            tech_slug = slugify_tech(tech_name)
            tech = get_one(session, Technology, slug=tech_slug)
            if tech is None:
                # Get category from mapping (TZ v3 requirement)
                category = TECHNOLOGIES_WITH_CATEGORIES.get(tech_name)
                tech = Technology(name=tech_name, slug=tech_slug, category=category, order_index=t_idx * 10)
                session.add(tech)
                session.flush()

            link = session.execute(
                select(ProjectTechnology).filter_by(project_id=proj.id, technology_id=tech.id)
            ).scalar_one_or_none()
            if link is None:
                session.add(ProjectTechnology(project_id=proj.id, technology_id=tech.id))


def seed_hero_tags(session):
    for idx, data in enumerate(HERO_TAGS_DATA, start=1):
        identity = {"id": idx}
        payload = {**data}
        upsert_one(session, HeroTag, identity, payload)


def seed_focus_areas(session):
    for idx, data in enumerate(FOCUS_AREAS_DATA, start=1):
        bullets = data.get("bullets", [])
        identity = {"id": idx}
        payload = {
            "title": data["title"],
            "is_primary": data.get("is_primary", False),
            "order_index": data.get("order_index", idx * 10),
        }
        focus: FocusArea = upsert_one(session, FocusArea, identity, payload)

        for b_idx, text in enumerate(bullets, start=1):
            bullet = session.execute(
                select(FocusAreaBullet).filter_by(
                    focus_area_id=focus.id,
                    text=text,
                )
            ).scalar_one_or_none()
            if bullet is None:
                bullet = FocusAreaBullet(
                    focus_area_id=focus.id,
                    text=text,
                    order_index=b_idx * 10,
                )
                session.add(bullet)


def seed_work_approaches(session):
    for idx, data in enumerate(WORK_APPROACHES_DATA, start=1):
        bullets = data.get("bullets", [])
        identity = {"id": idx}
        payload = {
            "title": data["title"],
            "icon": data.get("icon"),
            "order_index": data.get("order_index", idx * 10),
        }
        approach: WorkApproach = upsert_one(session, WorkApproach, identity, payload)

        for b_idx, text in enumerate(bullets, start=1):
            bullet = session.execute(
                select(WorkApproachBullet).filter_by(
                    work_approach_id=approach.id,
                    text=text,
                )
            ).scalar_one_or_none()
            if bullet is None:
                bullet = WorkApproachBullet(
                    work_approach_id=approach.id,
                    text=text,
                    order_index=b_idx * 10,
                )
                session.add(bullet)


def seed_section_meta(session):
    for idx, data in enumerate(SECTION_META_DATA, start=1):
        identity = {"section_key": data["section_key"]}
        payload = {
            "title": data.get("title"),
            "subtitle": data.get("subtitle"),
        }
        upsert_one(session, SectionMeta, identity, payload)


def run():
    with SessionLocal() as db:
        seed_profile(db)
        seed_contacts(db)
        seed_experience(db)
        seed_technologies(db)
        seed_projects_with_tech(db)
        seed_publications(db)
        seed_stats(db)
        seed_tech_focus(db)
        seed_hero_tags(db)
        seed_focus_areas(db)
        seed_work_approaches(db)
        seed_section_meta(db)

        db.commit()
        print("✔ Seed completed: ai_portfolio_new")


if __name__ == "__main__":
    run()
