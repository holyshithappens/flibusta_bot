#!/bin/bash
# 1. Очистить старые логи (сохраняя текущие)
sudo journalctl --vacuum-time=7d    # оставить логи за 7 дней
sudo find /var/log -name "*.gz" -delete    # удалить старые архивы

# 2. Очистить большие файлы
sudo truncate -s 0 /var/log/auth.log.1
sudo truncate -s 0 /var/log/btmp.1
sudo truncate -s 0 /var/log/syslog.1

# 3. Ротация логов вручную
sudo logrotate -f /etc/logrotate.conf

# 4. Проверить что осталось
sudo du -sh /var/log/*