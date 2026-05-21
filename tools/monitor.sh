#!/bin/bash

duration=${1:-240}  # время работы в минутах (по умолчанию 240)
end_time=$(( $(date +%s) + duration * 60 ))

echo "timestamp,cpu_usage(%),ram_usage(%),free_hdd(Mb)"

while true; do
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    cpu_usage=$(top -bn2 -p 1 | grep "Cpu(s)" | tail -n1 | awk '{print 100 - $8}')
    ram_usage=$(free | grep Mem | awk '{print int($3/$2 * 100.0)}')
    free_hdd_mb=$(df -m / | awk 'NR==2 {print $4}')

    echo "$timestamp,$cpu_usage,$ram_usage,$free_hdd_mb"

    if (( $(date +%s) >= end_time )); then
        break
    fi
    sleep 1
done