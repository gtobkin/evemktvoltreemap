# imports

# pull API calls

# verify our necessary API calls are supported

# pull market groups and store in .json file

# given market groups JSON file, construct market tree

# copy market tree; we now have trees for yesterday + today

# for each leaf, for yesterday + today, pull and calculate mkt vol

# trim leaves with 0 mkt vol both yesterday and today (is this really necessary?)

# for each leaf, calculate and store daily mkt vol change

# given today's mkt vol and daily change, generate Javascript array for Treemap

# save array in two locations: 1) datestamped archive copy 2) running "current" file for display
