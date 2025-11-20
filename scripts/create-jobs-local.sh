#!/bin/bash
# Create all Park4Night jobs by calling the API from local machine

API_URL="http://scraparr:8000"
SCRAPER_ID=1

echo "Creating Park4Night jobs for 29 European countries..."
echo ""

# Function to create a job
create_job() {
    local NAME="$1"
    local LAT_MIN="$2"
    local LAT_MAX="$3"
    local LON_MIN="$4"
    local LON_MAX="$5"
    local DAY="$6"
    local HOUR="$7"

    case $DAY in
        1) DAY_NAME="Monday";;
        2) DAY_NAME="Tuesday";;
        3) DAY_NAME="Wednesday";;
        4) DAY_NAME="Thursday";;
        5) DAY_NAME="Friday";;
        6) DAY_NAME="Saturday";;
        0) DAY_NAME="Sunday";;
    esac

    echo -n "Creating: $NAME ($DAY_NAME ${HOUR}:00)... "

    RESPONSE=$(curl -s -X POST "${API_URL}/api/jobs" \
      -H 'Content-Type: application/json' \
      -d "{
        \"scraper_id\": ${SCRAPER_ID},
        \"name\": \"Park4Night - ${NAME}\",
        \"description\": \"Weekly scrape: ${DAY_NAME} at ${HOUR}:00\",
        \"schedule_type\": \"cron\",
        \"schedule_config\": {\"expression\": \"0 ${HOUR} * * ${DAY}\"},
        \"params\": {
          \"lat_min\": ${LAT_MIN}, \"lat_max\": ${LAT_MAX},
          \"lon_min\": ${LON_MIN}, \"lon_max\": ${LON_MAX},
          \"grid_spacing\": 0.5, \"min_delay\": 1.0, \"max_delay\": 5.0,
          \"resume\": true
        },
        \"is_active\": true
      }")

    if echo "$RESPONSE" | grep -q '"id"'; then
        echo "✓"
    else
        echo "✗ (may already exist)"
    fi
}

# Create all jobs
create_job "UK" 49.5 61.0 -8.5 2.0 1 1
create_job "Ireland" 51.4 55.4 -10.5 -5.5 1 2
create_job "France" 41.0 51.5 -5.5 10.0 1 3
create_job "Spain" 36.0 43.8 -9.5 4.5 1 4
create_job "Portugal" 36.8 42.2 -9.5 -6.2 1 5

create_job "Italy" 36.5 47.0 6.5 18.5 2 1
create_job "Germany" 47.0 55.0 5.5 15.5 2 2
create_job "Netherlands" 50.7 53.6 3.2 7.3 2 3
create_job "Belgium" 49.5 51.5 2.5 6.5 2 4
create_job "Switzerland" 45.8 47.8 5.9 10.5 2 5

create_job "Austria" 46.4 49.0 9.5 17.2 3 1
create_job "Norway" 58.0 71.2 4.5 31.6 3 2
create_job "Sweden" 55.0 69.1 10.0 24.2 3 3
create_job "Finland" 59.8 70.1 19.5 31.6 3 4
create_job "Denmark" 54.5 57.8 8.0 15.2 3 5

create_job "Poland" 49.0 54.9 14.1 24.2 4 1
create_job "Czech Republic" 48.5 51.1 12.1 18.9 4 2
create_job "Slovakia" 47.7 49.6 16.8 22.6 4 3
create_job "Hungary" 45.7 48.6 16.1 22.9 4 4
create_job "Romania" 43.6 48.3 20.3 29.7 4 5

create_job "Greece" 34.8 41.8 19.3 28.3 5 1
create_job "Croatia" 42.4 46.5 13.5 19.4 5 2
create_job "Slovenia" 45.4 46.9 13.4 16.6 5 3
create_job "Bulgaria" 41.2 44.2 22.4 28.6 5 4
create_job "Serbia" 42.2 46.2 18.8 23.0 5 5

create_job "Estonia" 57.5 59.7 21.8 28.2 6 1
create_job "Latvia" 55.7 58.1 21.0 28.2 6 2
create_job "Lithuania" 53.9 56.5 20.9 26.8 6 3
create_job "Iceland" 63.3 66.6 -24.5 -13.5 6 4

echo ""
echo "✓ Job creation complete!"
echo ""
echo "View all jobs at: http://scraparr:3001"
echo "Or via API: curl http://scraparr:8000/api/jobs | python3 -m json.tool"
