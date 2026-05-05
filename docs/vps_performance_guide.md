# VPS Performance Control & Maintenance Reference Guide
## Ubuntu 22.04 LTS | Flibusta Bot + MariaDB in Docker

---

## Table of Contents

1. [Quick Status Commands](#1-quick-status-commands)
2. [System Resource Monitoring](#2-system-resource-monitoring)
3. [Docker Container Management](#3-docker-container-management)
4. [MariaDB Performance Monitoring](#4-mariadb-performance-monitoring)
5. [Bot Performance Monitoring](#5-bot-performance-monitoring)
6. [Common Maintenance Tasks](#6-common-maintenance-tasks)
7. [Troubleshooting](#7-troubleshooting)
8. [Performance Tuning](#8-performance-tuning)

---

## 1. Quick Status Commands

### One-Liner System Overview

```bash
# Complete system snapshot (CPU, RAM, Disk, Docker)
echo "=== SYSTEM ===" && uptime && echo "=== MEMORY ===" && free -h && echo "=== DISK ===" && df -h / && echo "=== DOCKER ===" && docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" && echo "=== DOCKER STATS ===" && docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Container Health Status

```bash
# Check if all containers are healthy
docker ps --filter "health=healthy"

# Detailed health info
docker inspect --format='{{.State.Health.Status}}' flibusta-db
docker inspect --format='{{.State.Health.Status}}' flibusta-bot
```

---

## 2. System Resource Monitoring

### 2.1 CPU Monitoring

```bash
# Current CPU usage (overall and per core)
top -bn1 | head -20

# Quick CPU summary
uptime

# Detailed CPU stats (includes load average)
mpstat -P ALL 1 1

# Per-process CPU usage
ps aux --sort=-%cpu | head -10
```

**Key Metrics:**
- Load average: should not exceed number of CPU cores (1.5 cores = 150% max for sustained)
- User CPU: normal operation 10-50%
- System CPU: should be < 20%

### 2.2 Memory Monitoring

```bash
# Memory usage summary
free -h

# Detailed memory info
cat /proc/meminfo

# Memory usage by process
ps aux --sort=-%mem | head -10
```

**Flibusta Bot Configuration:**
- Bot container: **256MB** limit (docker-compose.vps.yml)
- MariaDB container: **1GB** limit (docker-compose.vps.yml)
- MariaDB buffer pool: **1400M** (config/my.cnf.vps) - note: runs inside container with 1GB limit

**Memory Thresholds:**

| Usage | Status | Action |
|-------|--------|--------|
| < 60% | OK | None |
| 60-80% | Warning | Monitor closely |
| > 80% | Critical | Investigate immediately |
| > 90% | Emergency | Restart services |

### 2.3 Disk Monitoring

```bash
# Disk usage
df -h

# Disk I/O stats
iostat -x 1 2

# Largest directories
du -sh /var/* 2>/dev/null | sort -rh | head -10

# Check Docker disk usage
docker system df
```

**Disk Thresholds:**

| Usage | Status |
|-------|--------|
| < 70% | OK |
| 70-85% | Warning |
| > 85% | Critical |

---

## 3. Docker Container Management

### 3.1 Container Stats (Real-Time)

```bash
# Live stats for all containers
docker stats

# Live stats for specific container
docker stats flibusta-bot flibusta-db

# One-time stats snapshot
docker stats --no-stream flibusta-bot flibusta-db
```

**Output Format:**
```
CONTAINER           CPU %    MEM USAGE / LIMIT     MEM %    NET I/O           BLOCK I/O
flibusta-bot        0.12%    85.25MiB / 256MiB     33.30%   1.23MB / 512KB    0B / 0B
flibusta-db         2.45%    780.5MiB / 1GiB      76.52%   5.67MB / 2.34MB   12.3MB / 0B
```

### 3.2 Container Logs

```bash
# Bot logs (last 100 lines)
docker logs --tail 100 flibusta-bot

# Follow bot logs in real-time
docker logs -f flibusta-bot

# Bot logs with timestamps
docker logs -t flibusta-bot | tail -50

# MariaDB logs
docker logs --tail 100 flibusta-db

# Search logs for errors
docker logs flibusta-bot 2>&1 | grep -i error
docker logs flibusta-db 2>&1 | grep -i error

# Logs since specific time
docker logs --since 2026-03-09T00:00:00 flibusta-bot
```

### 3.3 Container Management

```bash
# Restart specific container
docker restart flibusta-bot
docker restart flibusta-db

# Stop/Start containers
docker stop flibusta-bot flibusta-db
docker start flibusta-bot flibusta-db

# Rebuild and restart (from project directory)
docker-compose -f docker-compose.vps.yml up -d --build

# View container processes
docker top flibusta-bot
docker top flibusta-db

# Container resource limits
docker inspect flibusta-bot | grep -A 10 '"Memory"'
docker inspect flibusta-db | grep -A 10 '"Memory"'
```

### 3.4 Docker System Maintenance

```bash
# Clean unused data
docker system prune -a

# Remove unused volumes (CAREFUL - removes database data!)
docker volume prune

# Full cleanup
docker system prune -a --volumes
```

---

## 4. MariaDB Performance Monitoring

### 4.1 Database Connection Status

```bash
# Enter MariaDB container
docker exec -it flibusta-db mysql -u flibusta -pflibusta flibusta

# Or with root
docker exec -it flibusta-db mysql -u root -prootpassword
```

### 4.2 Key Monitoring Queries

```sql
-- Database size
SELECT table_schema AS 'Database', 
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables 
GROUP BY table_schema;

-- Number of records per table
SELECT table_name, table_rows 
FROM information_schema.tables 
WHERE table_schema = 'flibusta' 
ORDER BY table_rows DESC;

-- Current connections
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';

-- Query cache status (deprecated in MariaDB 10.11+, but shown for reference)
SHOW STATUS LIKE 'Qcache%';

-- Buffer pool usage
SHOW STATUS LIKE 'Innodb_buffer_pool%';

-- Slow queries
SHOW GLOBAL STATUS LIKE 'Slow_queries';

-- Temporary tables
SHOW GLOBAL STATUS LIKE 'Created_tmp%';
```

### 4.3 Database Optimization

```sql
-- Analyze tables for better query optimization
ANALYZE TABLE book;
ANALYZE TABLE author;
ANALYZE TABLE sequence;
ANALYZE TABLE genre;

-- Check table sizes
SELECT table_name, ROUND(data_length/1024/1024, 2) AS 'Data (MB)', 
       ROUND(index_length/1024/1024, 2) AS 'Index (MB)'
FROM information_schema.tables 
WHERE table_schema = 'flibusta';
```

### 4.4 MariaDB Resource Usage

```bash
# Process list inside MariaDB
docker exec -it flibusta-db mysql -u root -prootpassword -e "SHOW PROCESSLIST;"

# Full process list with query info
docker exec -it flibusta-db mysql -u root -prootpassword -e "SHOW FULL PROCESSLIST;"
```

---

## 5. Bot Performance Monitoring

### 5.1 Bot Health Endpoints

The bot has built-in health monitoring via [`app/health.py`](app/health.py:19):

```python
# System stats available in code:
get_system_stats() -> {
    'memory_used': 'MB',
    'memory_percent': '%',
    'cpu_percent': '%',
    'open_files': count,
    'threads': count,
    'timestamp': 'ISO'
}
```

### 5.2 Bot Logs Analysis

```bash
# Recent errors
docker logs flibusta-bot 2>&1 | grep -E "(ERROR|CRITICAL|Exception)" | tail -20

# Memory warnings
docker logs flibusta-bot 2>&1 | grep -i memory | tail -10

# Database connection issues
docker logs flibusta-bot 2>&1 | grep -i "database\|mysql\|mariadb" | tail -10

# User activity
docker logs flibusta-bot 2>&1 | grep -i "user\|start\|message" | tail -20
```

### 5.3 Bot Memory Management

The bot performs periodic cleanup (see [`app/health.py`](app/health.py:127)):

```python
# Cleanup runs via job_queue:
# - Cleans inactive user sessions after CLEANUP_INTERVAL
# - Invalidates DB cache after cleanup
# - Logs system stats
```

To force cleanup:
```bash
# Check if bot is responsive
docker exec flibusta-bot ps aux
```

---

## 6. Common Maintenance Tasks

### 6.1 Log Rotation

```bash
# System logs (existing setup)
sudo journalctl --vacuum-time=7d
sudo find /var/log -name "*.gz" -delete

# Docker logs (add to /etc/logrotate.d/docker):
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
```

### 6.2 Database Backups

```bash
# Manual backup
docker exec flibusta-db mysqldump -u root -prootpassword flibusta > backup_$(date +%Y%m%d).sql

# Compressed backup
docker exec flibusta-db mysqldump -u root -prootpassword flibusta | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 6.3 System Updates

```bash
# Update package lists
sudo apt update

# View pending updates
sudo apt list --upgradable

# Install security updates
sudo apt upgrade -y

# Reboot if needed
sudo reboot
```

### 6.4 Docker Updates

```bash
# Pull latest images
docker-compose -f docker-compose.vps.yml pull

# Rebuild with new image
docker-compose -f docker-compose.vps.yml up -d --build
```

---

## 7. Troubleshooting

### 7.1 High CPU Usage

```bash
# Find top CPU processes
top -bn1 | head -20

# Docker-specific
docker stats --no-stream

# Check for runaway queries in DB
docker exec -it flibusta-db mysql -u root -prootpassword -e "SHOW FULL PROCESSLIST;"
```

**Solutions:**
- Bot: Check for infinite loops or excessive polling
- MariaDB: Optimize slow queries, increase buffer pool

### 7.2 High Memory Usage

```bash
# System memory
free -h

# Docker memory
docker stats --no-stream

# OOM killer logs
dmesg | grep -i "out of memory\|oom"
```

**Solutions:**
- Bot: Reduce user_data cache, restart container
- MariaDB: Reduce buffer pool size, add RAM

### 7.3 Container Won't Start

```bash
# Check logs
docker logs flibusta-bot
docker logs flibusta-db

# Inspect container
docker inspect flibusta-bot
docker inspect flibusta-db

# Check port conflicts
sudo netstat -tulpn | grep -E "3306|443|80"
```

### 7.4 Database Connection Issues

```bash
# Test connectivity from host
docker exec flibusta-bot ping db

# Test DB connection
docker exec flibusta-db mysql -u flibusta -pflibusta -e "SELECT 1;"

# Check DB health
docker inspect --format='{{.State.Health.Status}}' flibusta-db
```

---

## 8. Performance Tuning

### 8.1 Current Configuration Summary

| Component | Resource | Limit |
|-----------|----------|-------|
| Bot | Memory | 256 MB |
| Bot | CPU | 0.8 cores |
| MariaDB | Memory | 1 GB |
| MariaDB | CPU | 1.5 cores |
| MariaDB | Buffer Pool | 1400 MB (in container) |

### 8.2 MariaDB Tuning (config/my.cnf.vps)

Key settings in [`config/my.cnf.vps`](config/my.cnf.vps):

```ini
# InnoDB Buffer Pool - keep at ~70% of container memory
innodb-buffer-pool-size=1400M

# Connection limits
max-connections=50

# Query cache (disabled in MariaDB 10.11+)
query_cache_type=OFF

# SSD optimizations
innodb-io-capacity=2000
innodb-read-io-threads=4
innodb-write-io-threads=4
```

### 8.3 Docker Resource Adjustments

Edit [`docker-compose.vps.yml`](docker-compose.vps.yml) and restart:

```yaml
services:
  db:
    deploy:
      resources:
        limits:
          memory: 1.5G    # Increase if needed
          cpus: '2.0'    # Increase if needed
  bot:
    deploy:
      resources:
        limits:
          memory: 512M   # Increase if memory issues
          cpus: '1.0'
```

### 8.4 Quick Performance Checks

```bash
# Run existing monitor script (saves to CSV)
./tools/monitor.sh 60    # Monitor for 60 minutes

# Check disk I/O
iostat -x 1 5

# Network stats
netstat -s

# Container resource history
docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemPerc}}"
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Check all containers | `docker ps` |
| Container stats | `docker stats --no-stream` |
| Bot logs | `docker logs -f flibusta-bot` |
| DB logs | `docker logs -f flibusta-db` |
| Restart bot | `docker restart flibusta-bot` |
| Restart DB | `docker restart flibusta-db` |
| System info | `uptime && free -h && df -h /` |
| DB shell | `docker exec -it flibusta-db mysql -u root -prootpassword` |
| Full rebuild | `docker-compose -f docker-compose.vps.yml up -d --build` |
| Disk cleanup | `docker system prune -a` |

---

## File References

- [docker-compose.vps.yml](docker-compose.vps.yml) - Container configuration
- [config/my.cnf.vps](config/my.cnf.vps) - MariaDB settings
- [app/health.py](app/health.py) - Bot health monitoring
- [tools/monitor.sh](tools/monitor.sh) - System monitoring script
- [tools/df.sh](tools/df.sh) - Disk cleanup script
