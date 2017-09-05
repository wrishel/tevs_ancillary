/*

 This is step 1 for importing a dump file from TEVS on Ubuntu. Step 2 is
 done using psql as described in the comment below. Step 3 is the file
 import_from_tevs_2.sql.

 */

DROP SCHEMA pmitch CASCADE;
ALTER SCHEMA public RENAME TO public_stash;
CREATE SCHEMA public AUTHORIZATION tevs;

/*
 * Now psql -d tevs -v ON_ERROR_STOP=1 -f  <dump file from TEVS extraction>
 *
 * Then import_from_tevs_2.sql
 */

