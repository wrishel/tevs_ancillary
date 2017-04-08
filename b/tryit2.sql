--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

-- DROP INDEX public.voteops_filename_index;
-- ALTER TABLE ONLY public.voteops DROP CONSTRAINT voteops_pkey;
-- ALTER TABLE ONLY public.notes DROP CONSTRAINT notes_pkey;
-- ALTER TABLE ONLY public.ballots DROP CONSTRAINT ballots_pkey;
-- ALTER TABLE public.voteops ALTER COLUMN voteop_id DROP DEFAULT;
-- ALTER TABLE public.ocr_variants ALTER COLUMN id DROP DEFAULT;
-- ALTER TABLE public.notes ALTER COLUMN note_id DROP DEFAULT;
-- ALTER TABLE public.ballots ALTER COLUMN ballot_id DROP DEFAULT;
-- DROP SEQUENCE public.voteops_voteop_id_seq;
-- DROP TABLE public.voteops;
-- DROP TABLE public.trump;
-- DROP TABLE public.overvotes;
-- DROP TABLE public.overvote_values;
-- DROP TABLE public.overvote_ids;
-- DROP TABLE public.overvote_diffs;
-- DROP TABLE public.ov;
-- DROP SEQUENCE public.ocr_variants_id_seq;
-- DROP TABLE public.ocr_variants;
-- DROP SEQUENCE public.notes_note_id_seq;
-- DROP TABLE public.notes;
-- DROP TABLE public.clinton;
-- DROP SEQUENCE public.ballots_ballot_id_seq;
-- DROP TABLE public.ballots;
-- DROP EXTENSION plpgsql;
-- DROP SCHEMA public;
--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- CREATE SCHEMA public;


-- ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

-- COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: ballots; Type: TABLE; Schema: public; Owner: tevs; Tablespace: 
--

CREATE TABLE ballots (
    ballot_id integer NOT NULL,
    processed_at timestamp without time zone,
    code_string character varying(80),
    layout_code bigint,
    file1 character varying(80),
    file2 character varying(80),
    precinct character varying(80),
    party character varying(80)
);


ALTER TABLE public.ballots OWNER TO tevs;
