truncate t_harts_wi_condensed_grp;

insert into t_harts_wi_condensed_grp
	select * from n_harts_WI_condensed_grp_2;

