\echo '----------'  n_inconsistency_cnts_format '----------'

drop view n_inconsistency_cnts_format ;
create or replace view n_inconsistency_cnts_format as
select 
    "Inconsistencies",
    count(*) as "Number of Voteops"
FROM n_tevs_v_hart_format
group by "Inconsistencies"
order by     case
        when "Inconsistencies" ~ '^[0-9]+$' THEN "Inconsistencies"::Integer
        else 999999
    END  


;
alter table n_inconsistency_cnts_format owner to tevs