CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_portfolio_user') THEN
    CREATE ROLE ai_portfolio_user WITH LOGIN PASSWORD 'ai-portfolio123';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'ai_portfolio') THEN
    CREATE DATABASE ai_portfolio OWNER ai_portfolio_user;
  END IF;
END $$;

ALTER DATABASE ai_portfolio OWNER TO ai_portfolio_user;
GRANT ALL PRIVILEGES ON DATABASE ai_portfolio TO ai_portfolio_user;
