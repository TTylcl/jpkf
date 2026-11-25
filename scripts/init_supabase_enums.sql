-- ============================================================
-- init_supabase_enums.sql
-- 在 Supabase SQL editor 里先跑这一步，再运行 seed_data.py / 启动应用
-- 原因：模型里 6 个 PGEnum 都设置了 create_type=False，
--       SQLAlchemy 的 create_all() 不会创建这些枚举类型，
--       但建表 DDL 会引用它们，全新库上会报 "type ... does not exist"。
-- 每个块用 DO $$ ... EXCEPTION WHEN duplicate_object 包裹，可重复执行。
-- ============================================================

DO $$ BEGIN
  CREATE TYPE user_type_enum AS ENUM ('STUDENT','TEACHER','ADMIN','PARENT');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE course_type_enum AS ENUM ('REGULAR','TRIAL','SUMMER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE schedule_status_enum AS ENUM ('pending','approved','rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE session_type_enum AS ENUM ('AI_SERVICE','HUMAN_SERVICE','TRANSFER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE sender_type_enum AS ENUM ('USER','ROBOT','HUMAN','SYSTEM');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE message_type_enum AS ENUM ('TEXT','IMAGE','CARD','VOICE','FILE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
