\d voteops

-- select *
-- from pg_class
-- where 
-- 	relname not like 'pg_%' and
-- 	relname not like '_pg_%'
-- order by relname

;
\quit
select * from pg_depend
join relname on
	classid = 
where deptype ='n'