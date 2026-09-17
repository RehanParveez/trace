DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'trace_runtime') THEN
        CREATE ROLE trace_runtime LOGIN PASSWORD 'trace_runtime_dev_pw';
    ELSE
        ALTER ROLE trace_runtime LOGIN PASSWORD 'trace_runtime_dev_pw';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE trace TO trace_runtime;
GRANT USAGE ON SCHEMA public TO trace_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE trace IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trace_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE trace IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO trace_runtime;