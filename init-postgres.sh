#!/bin/bash
set -e

# This script is automatically run by PostgreSQL on container startup
# if placed in /docker-entrypoint-initdb.d/

echo "========================================"
echo "Initializing PostgreSQL databases..."
echo "========================================"
echo ""

# Create the application database and user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create application user
    CREATE USER ${APP_DB_USER} WITH PASSWORD '${APP_DB_PASSWORD}';

    -- Enable UUID extension
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Create application database
    CREATE DATABASE ${APP_DB_NAME} OWNER ${APP_DB_USER};

    -- Grant necessary privileges
    GRANT ALL PRIVILEGES ON DATABASE ${APP_DB_NAME} TO ${APP_DB_USER};

    -- Connect to the new database and grant schema privileges
    \c ${APP_DB_NAME}
    GRANT ALL ON SCHEMA public TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${APP_DB_USER};
EOSQL

# Now create the users table in the application database
psql -v ON_ERROR_STOP=1 --username "$APP_DB_USER" --dbname "$APP_DB_NAME" <<-EOSQL
    -- Enable UUID extension in application database
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Create users table with UUID primary key
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'JOB_SEEKER',
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

    -- Insert default admin user (password: admin123)
    -- Hash generated with bcrypt: admin123
    INSERT INTO users (email, name, hashed_password, role, is_active, is_superuser)
    VALUES (
        'admin@hr-automation.com',
        'System Administrator',
        '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7TiX.MvHc2',
        'ADMIN',
        true,
        true
    ) ON CONFLICT (email) DO NOTHING;
EOSQL

echo ""
echo "========================================"
echo "PostgreSQL initialization completed!"
echo "========================================"
echo "Database: ${APP_DB_NAME}"
echo "User: ${APP_DB_USER}"
echo "Default admin: admin@hr-automation.com / admin123"
echo ""
