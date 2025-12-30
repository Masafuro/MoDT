-- ユーザー情報を管理する基本テーブル
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 動作確認用のテストユーザー（パスワードは 'password' を想定したダミー）
INSERT INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$ExampleHashValue...', 'admin')
ON CONFLICT (username) DO NOTHING;