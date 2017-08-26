select file1 from n_bal_voteops_not_excluded
where precinct_code_string = '000002'
and was_voted and choice_text = 'YES'