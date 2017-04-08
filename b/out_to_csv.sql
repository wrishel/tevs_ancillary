-- \copy (select * from n_interest_stats) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/n_interest_stats.csv' (format csv, delimiter ',', header)

-- \copy (select * from n_tevs_v_hart_by_precinct_format) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/tevs_v_hart_by_pct_1.csv' (format csv, delimiter ',', header)


-- \copy (select * from n_overall_tevs_v_hart) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/verall_tevs_v_hart.csv' (format csv, delimiter ',', header)

\echo 'creating n_tevs_v_hart_format_5.csv'
\copy (select * from n_tevs_v_hart_format_5) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/tevs_v_hart.10.csv' (format csv, delimiter ',', header)

-- \echo 'creating n_margin_report_format.csv'
-- \copy (select * from n_margin_report_format) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/margin_report.csv' (format csv, delimiter ',', header)

-- \echo 'creating n_tevs_v_hart_8.csv'
-- \copy (select * from n_tevs_v_hart_9) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/n_tevs_v_hart_9.csv' (format csv, delimiter ',', header)

-- \copy (select * from n_tevs_v_hart_9) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/n_tevs_v_hart_9.3.csv' (format csv, delimiter ',', header)

-- \echo 'creating n_hart_precinct.csv'
-- \copy (select * from n_hart_precinct) to '/Users/Wes/Dropbox/Programming/ElectionTransparency/n_hart_precinct.csv' (format csv, delimiter ',', header)
