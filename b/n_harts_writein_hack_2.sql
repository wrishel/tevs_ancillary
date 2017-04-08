\echo '----------'  n_harts_writein_hack_2 '----------'
-- drop view n_harts_writein_hack_2;
-- create or replace view n_harts_writein_hack_2 AS

select   
        precinct_name as precinct_harts,
        contest_title,
        candidate_name,
        total_votes,
        total_ballots

from harts
;
-- 8241 rows out of 8441 = 200 fewer consistent with 400 total writeins of two varieties
-- alter table n_harts_writein_hack_2 owner to tevs
