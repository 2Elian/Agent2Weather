#!/bin/bash
echo "Waiting for SQL Server to start..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if /opt/mssql-tools/bin/sqlcmd \
        -S $DATABASE_HOST,$DATABASE_PORT \
        -U $DATABASE_USERNAME \
        -P $DATABASE_PASSWORD \
        -Q "SELECT 1" > /dev/null 2>&1; then
        echo "SQL Server is ready!"
        break
    fi
    echo "Waiting for SQL Server... (attempt $attempt/$max_attempts)"
    sleep 5
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "Error: SQL Server did not start in time"
    exit 1
fi

echo "Creating database $DATABASE_NAME if not exists..."
/opt/mssql-tools/bin/sqlcmd \
    -S $DATABASE_HOST,$DATABASE_PORT \
    -U $DATABASE_USERNAME \
    -P $DATABASE_PASSWORD \
    -Q "IF NOT EXISTS(SELECT * FROM sys.databases WHERE name = '$DATABASE_NAME') BEGIN CREATE DATABASE [$DATABASE_NAME] END"

if [ -d "/app/data/sql" ]; then
    echo "Found SQL files in /app/data/sql, executing..."
    
    # 按文件名排序执行
    for sql_file in $(ls /app/data/sql/*.sql | sort); do
        echo "Executing: $sql_file"
        /opt/mssql-tools/bin/sqlcmd \
            -S $DATABASE_HOST,$DATABASE_PORT \
            -U $DATABASE_USERNAME \
            -P $DATABASE_PASSWORD \
            -d $DATABASE_NAME \
            -i "$sql_file"
        
        if [ $? -eq 0 ]; then
            echo "Successfully executed: $sql_file"
        else
            echo "Error executing: $sql_file"
        fi
    done
    echo "All SQL files have been executed."
else
    echo "No SQL files found in /app/data/sql"
fi