DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'trace_runtime') THEN
    CREATE ROLE trace_runtime LOGIN PASSWORD 'trace_runtime_dev_pw' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  ELSE
    ALTER ROLE trace_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE trace TO trace_runtime;
GRANT USAGE ON SCHEMA public TO trace_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trace_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trace_runtime;

-- tables and sequences the owner creates later (new migrations) are granted automatically
ALTER DEFAULT PRIVILEGES FOR ROLE trace IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trace_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE trace IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO trace_runtime;

-- the helper the policies call
GRANT EXECUTE ON FUNCTION support_grant_active(uuid) TO trace_runtime;

-- the runtime role is not allowed to change schema
REVOKE CREATE ON SCHEMA public FROM trace_runtime;

SELECT rolname, rolsuper, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname = 'trace_runtime';
