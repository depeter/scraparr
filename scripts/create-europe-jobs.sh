#!/bin/bash
#
# Create Park4Night scraping jobs for all European countries
# Each country gets a weekly job scheduled at different times
#

set -e

SERVER="scraparr"
API_URL="http://localhost:8000"

echo "========================================="
echo "Creating Park4Night Jobs for Europe"
echo "========================================="
echo ""

# Array of countries with their coordinates and schedule
# Format: name|lat_min|lat_max|lon_min|lon_max|day_of_week|hour
declare -a COUNTRIES=(
    "UK|49.5|61.0|-8.5|2.0|1|1"
    "Ireland|51.4|55.4|-10.5|-5.5|1|2"
    "France|41.0|51.5|-5.5|10.0|1|3"
    "Spain|36.0|43.8|-9.5|4.5|1|4"
    "Portugal|36.8|42.2|-9.5|-6.2|1|5"
    "Italy|36.5|47.0|6.5|18.5|2|1"
    "Germany|47.0|55.0|5.5|15.5|2|2"
    "Netherlands|50.7|53.6|3.2|7.3|2|3"
    "Belgium|49.5|51.5|2.5|6.5|2|4"
    "Switzerland|45.8|47.8|5.9|10.5|2|5"
    "Austria|46.4|49.0|9.5|17.2|3|1"
    "Norway|58.0|71.2|4.5|31.6|3|2"
    "Sweden|55.0|69.1|10.0|24.2|3|3"
    "Finland|59.8|70.1|19.5|31.6|3|4"
    "Denmark|54.5|57.8|8.0|15.2|3|5"
    "Poland|49.0|54.9|14.1|24.2|4|1"
    "Czech Republic|48.5|51.1|12.1|18.9|4|2"
    "Slovakia|47.7|49.6|16.8|22.6|4|3"
    "Hungary|45.7|48.6|16.1|22.9|4|4"
    "Romania|43.6|48.3|20.3|29.7|4|5"
    "Greece|34.8|41.8|19.3|28.3|5|1"
    "Croatia|42.4|46.5|13.5|19.4|5|2"
    "Slovenia|45.4|46.9|13.4|16.6|5|3"
    "Bulgaria|41.2|44.2|22.4|28.6|5|4"
    "Serbia|42.2|46.2|18.8|23.0|5|5"
    "Estonia|57.5|59.7|21.8|28.2|6|1"
    "Latvia|55.7|58.1|21.0|28.2|6|2"
    "Lithuania|53.9|56.5|20.9|26.8|6|3"
    "Iceland|63.3|66.6|-24.5|-13.5|6|4"
)

SCRAPER_ID=1  # Park4Night Grid Scraper ID
JOBS_CREATED=0

for country_data in "${COUNTRIES[@]}"; do
    IFS='|' read -r NAME LAT_MIN LAT_MAX LON_MIN LON_MAX DAY HOUR <<< "$country_data"

    # Day names for display
    case $DAY in
        1) DAY_NAME="Monday";;
        2) DAY_NAME="Tuesday";;
        3) DAY_NAME="Wednesday";;
        4) DAY_NAME="Thursday";;
        5) DAY_NAME="Friday";;
        6) DAY_NAME="Saturday";;
        0) DAY_NAME="Sunday";;
    esac

    echo "Creating job: $NAME ($DAY_NAME ${HOUR}:00)"

    # Create job via API
    RESPONSE=$(curl -s -X POST "${API_URL}/api/jobs" \
      -H 'Content-Type: application/json' \
      -d "{
        \"scraper_id\": ${SCRAPER_ID},
        \"name\": \"Park4Night - ${NAME} Weekly\",
        \"description\": \"Weekly scrape of ${NAME} camping spots - ${DAY_NAME} at ${HOUR}:00 AM\",
        \"schedule_type\": \"cron\",
        \"schedule_config\": {
          \"expression\": \"0 ${HOUR} * * ${DAY}\"
        },
        \"params\": {
          \"lat_min\": ${LAT_MIN},
          \"lat_max\": ${LAT_MAX},
          \"lon_min\": ${LON_MIN},
          \"lon_max\": ${LON_MAX},
          \"grid_spacing\": 0.5,
          \"min_delay\": 1.0,
          \"max_delay\": 5.0,
          \"resume\": true
        },
        \"is_active\": true
      }")

    # Check if successful
    if echo "$RESPONSE" | grep -q '"id"'; then
        JOB_ID=$(echo "$RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
        echo "  ✓ Created job #${JOB_ID}"
        ((JOBS_CREATED++))
    else
        echo "  ✗ Failed: $RESPONSE"
    fi

    # Small delay between requests
    sleep 0.5
done

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo "Jobs created: ${JOBS_CREATED} / ${#COUNTRIES[@]}"
echo ""
echo "View all jobs:"
echo "  curl ${API_URL}/api/jobs | python3 -m json.tool"
echo ""
echo "Or visit: http://scraparr:3001"
echo ""
echo "Done!"
