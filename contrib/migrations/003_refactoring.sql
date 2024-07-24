ALTER TABLE users DROP COLUMN chat_id;

ALTER TABLE chat_messages ADD COLUMN user_id BIGINT;
UPDATE chat_messages SET user_id = chat_id;
ALTER TABLE chat_messages ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id);
