 \echo '----------'  n_tevs_v_hart_format_5 '----------'
select NULL as n_tevs_v_hart_format_5;

drop view n_tevs_v_hart_format_5;

CREATE OR REPLACE VIEW n_tevs_v_hart_format_5 AS 
 SELECT 
    tvh.precinct_tevs               as "Precinct TEVS",
    tvh.ballot_page                 as "Ballot Page",
    tvh.ballot_side                 as "ballot Side",
    array_to_string(bb.ballot_batches, ' ')
                                    as "Ballot Batches",
    tvh.contest_tevs                AS "Contest TEVS",
    tvh.choice_tevs                 AS "Choice TEVS",
    tvh.tevs_counts_counted         AS "TEVS Voteops Marked",
    tvh.tevs_tot_voteops            as "TEVS Total Voteops",
    tvh.tevs_counts_not_counted     AS "TEVS Voteops not Marked",
    tvh.tevs_tot_overvotes          as "TEVS Over Votes",

    ('~  ' || tvh.precinct_harts)   as "Precinct HART",
    left(tvh.contest_harts, 23)     as "Contest HART",
    left(tvh.choice_harts, 21)      as "Choice HART",
    tvh.hart_count                  AS "HART Count",
    tvh.harts_ballots               as "HART Ballots",

    tvh.tevs_minus_hart             AS "Votes Counted TEVS Minus HART",
    tvh.voteops_tev_minus_hart      as "Total Voteops TEVS Minus HART",
    abs(tvh.tevs_minus_hart)        AS "ABS Votes Counted TEVS Minus HART",
    abs(tvh.voteops_tev_minus_hart) as "ABS Total Voteops TEVS Minus HART",
    tvh.margin                      as "Margin",
    case 
      when tvh.margin = 0 then '--'
      else 
        to_char(abs(tvh.tevs_minus_hart)/tvh.margin*100, '990.00%')
      end
                                    as "Error Pct",

    (coalesce(tvh.precinct_harts, precinct_harts_mapped)  || '.' ||
     coalesce(tvh.contest_harts, contest_harts_mapped) || '.' ||
     coalesce(tvh.choice_harts, choice_harts_mapped))
                                    as "Sort Key"

  FROM n_tevs_v_hart_10 as tvh
  JOIN n_ballot_batches_1 bb
    ON 
      bb.precinct_code_string=tvh.precinct_tevs AND  
      bb.contest_text=tvh.contest_tevs AND 
      bb.choice_text=tvh.choice_tevs
  ORDER BY 
    coalesce(tvh.precinct_harts, precinct_harts_mapped),
    coalesce(tvh.contest_harts, contest_harts_mapped),
    coalesce(tvh.choice_harts, choice_harts_mapped)
;


