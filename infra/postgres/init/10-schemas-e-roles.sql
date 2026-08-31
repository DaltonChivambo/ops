-- Um schema E um role por serviço, com GRANT apenas no próprio schema.
-- O isolamento é imposto pela base de dados, não pela boa vontade da equipa.
-- JOIN entre schemas é impossível para o role do serviço: não tem USAGE nos outros.
--
-- ATENÇÃO: as passwords aqui são de desenvolvimento. Em produção vêm de secrets.

DO $$
DECLARE
    servico   text;
    servicos  text[] := ARRAY['auth','ticketing','asset','approval','notification','reporting'];
BEGIN
    FOREACH servico IN ARRAY servicos LOOP
        -- role
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = servico || '_svc') THEN
            EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', servico || '_svc', servico || '_dev_pw');
        END IF;

        -- schema, propriedade do role do serviço
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION %I', servico, servico || '_svc');

        -- nada no schema public: evita que uma tabela escape para lá por descuido
        EXECUTE format('REVOKE ALL ON SCHEMA public FROM %I', servico || '_svc');

        -- o role só vê o seu próprio schema
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO %I', servico, servico || '_svc');
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I
             GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
            servico || '_svc', servico, servico || '_svc');
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I
             GRANT USAGE, SELECT ON SEQUENCES TO %I',
            servico || '_svc', servico, servico || '_svc');

        -- search_path fixo: o serviço nunca precisa de qualificar tabelas
        EXECUTE format('ALTER ROLE %I SET search_path TO %I', servico || '_svc', servico);
    END LOOP;
END
$$;

-- Verificação (secção 8 do ARCHITECTURE.md):
--   \c ops ticketing_svc
--   SELECT * FROM asset.ativos;   -->  ERROR: permission denied for schema asset
