ALTER TABLE users DROP COLUMN chat_id;

ALTER TABLE chat_messages ADD COLUMN user_id INTEGER;
UPDATE chat_messages SET user_id = chat_id;
ALTER TABLE chat_messages ALTER COLUMN user_id SET REFERENCES users(user_id);
