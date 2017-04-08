select 
count(*),
"Interest Level"
from n_tevs_v_hart_format_5
Group by "Interest Level"
Order by "Interest Level"
;
select sum(count) 
from (select 
count(*),
"Interest Level"
from n_tevs_v_hart_format_5
Group by "Interest Level"
Order by "Interest Level") subq
