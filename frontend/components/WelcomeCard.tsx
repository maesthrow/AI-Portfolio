// frontend/app/components/WelcomeCard.tsx
import Avatar from "./Avatar";

export default function WelcomeCard() {
  return (
    <section
      aria-labelledby="welcome"
      className="card bio"
      style={{
        padding: 22,                 // было 18 — добавили воздуха
      }}
    >
      {/* Левая колонка: аватар */}
      <div className="avatar" style={{ marginRight: 16 }}>
        <Avatar src="/avatar.webp" initials="DK" />
      </div>

      {/* Правая колонка: контент */}
      <div
        className="content"
        style={{
          width: "100%",
          display: "grid",
          rowGap: 12,                // базовый вертикальный ритм внутри
        }}
      >
        <div
          className="head"
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 10,
            marginBottom: 4,         // +чуть отступ под заголовком
          }}
        >
          <h2 id="welcome" style={{ margin: 0 }}>Привет, меня зовут Дмитрий</h2>
        </div>

        <div
          className="head"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            marginTop: 2,
            marginBottom: 12,        // было 10 — немного больше
          }}
        >
          <span className="role">Python-разработчик</span>
          <span className="role">ML-инженер</span>
        </div>

        <p
          className="lead"
          style={{
            margin: 0,
            lineHeight: 1.7,         // было 1.6 — читается свободнее
            color: "rgba(255,255,255,0.92)",
          }}
        >
          Добро пожаловать на мой сайт — интерактивное портфолио.
          <br />
          Справа внизу живет AI-агент,
          который отвечает на вопросы о моем опыте и проектах по данным, которые я загрузил
          в свою БД и векторное хранилище.
        </p>

        <div
          className="links"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,                 // было 10
            marginTop: 12,           // было 12 — немного ниже от основного текста
          }}
        >
          <a href="https://github.com/maesthrow" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <span className="dot">•</span>
          <a href="https://t.me/kargindmitriy" target="_blank" rel="noreferrer">
            Telegram
          </a>
        </div>
      </div>
    </section>
  );
}
