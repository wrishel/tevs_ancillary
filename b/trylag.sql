

select 
	file1, prev_file1
from
	(select 
		file1, 
		left(right(file1,10),6)::bigint as file1_num,
		prev_file1,
		left(right(prev_file1,10),6)::bigint as prev_file1_num
	from
		(select file1, lag(file1) over(order by file1) as prev_file1
			from ballots
			order by file1) as files1
	order by file1) as file1_vs_prev
where (file1_num - prev_file1_num) > 1
;
select file1 from ballots order by file1
;
