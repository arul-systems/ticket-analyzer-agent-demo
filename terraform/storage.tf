# Results bucket the Cloud Run function writes one JSON file per processed
# ticket to (named <ticket_id>.json - see agent/results.py). Separate from
# the function_source bucket in function.tf, which only holds the
# placeholder deploy package.


