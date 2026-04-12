#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/wifi-tracker/backups"
mkdir -p $BACKUP_DIR
cp /opt/wifi-tracker/wifi_tracker.db $BACKUP_DIR/wifi_tracker_$DATE.db
# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
